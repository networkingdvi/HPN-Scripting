# Auto-deploy port-settings based on csv-file on HPE Comware 7 switches
#
#-------------------------------------------------------------------------------
# Author:      Remi Batist / AXEZ ICT Solutions
# Version:     2.0
#
# Created:     15-04-2016
# Comments:    remi.batist@axez.nl
#-------------------------------------------------------------------------------
#
# Required row format shown in the example below
# csv delimiter ' ; '

# interface-name        aggregation-number  aggregation-description     interface-description   linktype    permitted-vlan  pvid
# GigabitEthernet1/0/1  15                  Server-1                    Server-1-nic1           trunk       20 21           20
# GigabitEthernet1/0/2                                                  server-2                access                      23
# GigabitEthernet1/0/3                                                  ups-mgmt                access                      15
# ...
# GigabitEthernet2/0/1  15                  Server-1                    Server-1-nic2           trunk       20 21           20
# ...


import time
import sys
import csv
import comware
import termios

#### RAW user-input module
fd = sys.stdin.fileno();
new = termios.tcgetattr(fd)
new[3] = new[3] | termios.ICANON | termios.ECHO
new[6] [termios.VMIN] = 1
new[6] [termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, new)
termios.tcsendbreak(fd,0)

class InterfaceConfig():

    def __init__(self):
        self.config_dict = {}
        self.bridge_dict = {'desc': [], 'lnk_type': [], 'pvid': [], 'pvln': []}
        self.counter = 0
        pass

    def importData(self):
        myfile = raw_input('Enter filename: ')
        try:
            src_file = open(myfile)
            try:
                print 'Reading file.....', src_file.name
                reader = csv.DictReader(src_file, delimiter=';')
                ### Creating a list of dictionaries
                self.imported_data = list(reader)
            finally:
                print 'Closing file.....', src_file.name
                src_file.close()
        except IOError as e:
            print("\nError %d reading file ' %s '\n" % (e.errno, e.filename) )
            quit()

    def removeData(self):
        print "Checking for unconfigured interfaces in data..."
        for line_number in reversed(range(len(self.imported_data))):
            if not self.imported_data[line_number]['linktype']:
                print 'deleting interface', self.imported_data[line_number]['interface-name']
                del self.imported_data[line_number]

    def checkData(self):
        print "Checking configured interfaces in data..."
        for row in self.imported_data:
            self.counter += 1
            ##linktype check
            row['linktype'] = row['linktype'].lower().replace(' ', '')
            while row['linktype'] and not any ([row['linktype'] == 'access', row['linktype'] == 'trunk']):
                row['linktype'] = raw_input('Incorrect linktype for  ' + row['interface-name'] + ', enter linktype (access/trunk): ')
            ##permitvlan check
            row['permitted-vlan'] = row['permitted-vlan'].replace(",", " ").replace("-", " to ")
            if row['linktype'] == 'trunk':
                while not (row['permitted-vlan']):
                    (row['permitted-vlan']) = raw_input('Permitted-vlan is missing for ' + row['interface-name'] + ':, \nEnter new VLAN (1 - 4096): ')
                while not unicode(row['permitted-vlan']).replace(' to ', '').replace(' ', '').isdecimal():
                    (row['permitted-vlan']) = raw_input('Permitted-vlan is incorrect for ' + row['interface-name'] + ':, \nEnter new VLAN (1 - 4096): ')
            ##pvid check
            while row['pvid'] and not unicode(row['pvid']).isdecimal():
                (row['pvid']) = raw_input('PVID is incorrect for ' + row['interface-name'] + ':, \nEnter new PVID (1 - 4096): ')
            if unicode(row['pvid']).isdecimal() and int(row['pvid']) == 1:
                (row['pvid']) = ''
            ##aggregation-number check
            while row['aggregation-number'] and not unicode(row['aggregation-number']).isdecimal() or unicode(row['aggregation-number']).isdecimal() and int(row['aggregation-number']) > 1024:
                (row['aggregation-number']) = raw_input('Imported BridgeID is incorrect for ' + row['interface-name'] + ': [' + row['aggregation-number'] + '], \nEnter new BridgeID (1 - 1024): ')


    def prepareInterface(self):
        for row in self.imported_data:
            try:
                if unicode(row['aggregation-number']).isdecimal() and self.config_dict[('Bridge-Aggregation ' + row['aggregation-number'])]:
                    print 'Bridge-aggregation already exists', row['aggregation-number']
                    self.config_dict.setdefault(row['interface-name'],[]).append('default ; ' + 'port link-aggregation group ' + row['aggregation-number'])
            except KeyError:
                print 'Creating Bridge-aggregation', row['aggregation-number']
                self.config_dict.setdefault('Bridge-Aggregation ' + row['aggregation-number'],[]).append('default ; link-aggregation mode dynamic')
                self.config_dict.setdefault(row['interface-name'],[]).append('default ; ' + 'port link-aggregation group ' + row['aggregation-number'])
            if not row['aggregation-number']:
                self.config_dict.setdefault(row['interface-name'],[]).append('default')


    def processDescription(self):
        for row in self.imported_data:
            if row['aggregation-description']:
                if unicode(row['aggregation-number']).isdecimal() and not ('Bridge-Aggregation ' + row['aggregation-number'] in self.bridge_dict['desc']):
                    self.bridge_dict.setdefault('desc',[]).append('Bridge-Aggregation ' + row['aggregation-number'])
                    self.config_dict.setdefault('Bridge-Aggregation ' + row['aggregation-number'],[]).append('description ' + row['aggregation-description'])
            if row['interface-description']:
                self.config_dict.setdefault(row['interface-name'],[]).append('description ' + row['interface-description'])

    def processLinktype(self):
        for row in self.imported_data:
            if unicode(row['aggregation-number']).isdecimal() and not ('Bridge-Aggregation ' + row['aggregation-number'] in self.bridge_dict['lnk_type']):
                self.bridge_dict.setdefault('lnk_type',[]).append('Bridge-Aggregation ' + row['aggregation-number'])
                self.config_dict.setdefault('Bridge-Aggregation ' + row['aggregation-number'],[]).append('port link-type ' + row['linktype'])
            self.config_dict.setdefault(row['interface-name'],[]).append('port link-type ' + row['linktype'])

    def processPVID(self):
        for row in self.imported_data:
            if row['linktype'] == 'trunk':
                if unicode(row['pvid']).isdecimal():
                    pvid_command = 'port trunk pvid vlan '
                else:
                    pvid_command = 'port trunk pvid vlan 1'
            if row['linktype'] == 'access':
                if unicode(row['pvid']).isdecimal():
                    pvid_command = 'port access vlan '
                else:
                    pvid_command = 'undo port access vlan'
            if unicode(row['aggregation-number']).isdecimal() and not ('Bridge-Aggregation ' + row['aggregation-number'] in self.bridge_dict['pvid']):
                self.bridge_dict.setdefault('pvid',[]).append('Bridge-Aggregation ' + row['aggregation-number'])
                self.config_dict.setdefault('Bridge-Aggregation ' + row['aggregation-number'],[]).append(pvid_command + row['pvid'])
            self.config_dict.setdefault(row['interface-name'],[]).append(pvid_command + row['pvid'])

    def processPermitvlan(self):
        for row in self.imported_data:
            finalSplit = tempSplit = ''
            if row['linktype'] == 'trunk':
                countVlans = len(row['permitted-vlan'].split())
                if countVlans > 10:
                    sortVlans = (row['permitted-vlan'].split())
                    for prev,cur,next in zip([None]+sortVlans[:-1], sortVlans, sortVlans[1:]+[None]):
                        countVlans = len(tempSplit.split())
                        if (countVlans == 8 and next == 'to' or countVlans == 9 and next == 'to'):
                            finalSplit += ("; port trunk permit vlan " + str(tempSplit))
                            tempSplit = ''
                        tempSplit += (cur  + " ")
                        countVlans = len(tempSplit.split())
                        if countVlans == 10:
                            finalSplit += ("; port trunk permit vlan " + str(tempSplit))
                            tempSplit = ''
                    if countVlans > 0:
                        finalSplit += ("; port trunk permit vlan " + str(tempSplit))
                else:
                    finalSplit += ("port trunk permit vlan " + row['permitted-vlan'])
                if unicode(row['aggregation-number']).isdecimal() and not ('Bridge-Aggregation ' + row['aggregation-number'] in self.bridge_dict['pvln']):
                    self.bridge_dict.setdefault('pvln',[]).append('Bridge-Aggregation ' + row['aggregation-number'])
                    self.config_dict.setdefault('Bridge-Aggregation ' + row['aggregation-number'],[]).append(str(finalSplit))
                    if ' 1 ' not in row['permitted-vlan']:
                        self.config_dict.setdefault('Bridge-Aggregation ' + row['aggregation-number'],[]).append('undo port trunk permit vlan 1')
                self.config_dict.setdefault(row['interface-name'],[]).append(str(finalSplit))
                if ' 1 ' not in row['permitted-vlan']:
                    self.config_dict.setdefault(row['interface-name'],[]).append('undo port trunk permit vlan 1')

    def deployConfig(self):
        for interface in sorted(self.config_dict):
            finalConfig = ''
            for config in self.config_dict[interface]:
                finalConfig += ' ; ' +config
            comware.CLI('system ; interface ' + interface + finalConfig)
            #print ('system ; interface ' + interface + finalConfig)
        print '\n#### ', self.counter, 'interfaces configured! ####'


def main():
    try:
        ifc = InterfaceConfig()
        ifc.importData()
        ifc.removeData()
        ifc.checkData()
        ifc.prepareInterface()
        ifc.processDescription()
        ifc.processLinktype()
        ifc.processPVID()
        ifc.processPermitvlan()
        ifc.deployConfig()
    except (EOFError, KeyboardInterrupt):
        print "\n\nquiting script!!!...."
        quit()

if __name__ == "__main__":
	main()

