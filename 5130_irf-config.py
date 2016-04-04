
__author__ = 'Remi Batist / AXEZ ICT Solutions'
__version__ = '2.5'
__comments__= 'remi.batist@axez.nl'
###     Deploying (IRF-)(iMC-)config and software on HP5130 24/48 Ports (PoE) Switches #########

###     version 1.0: first release (support for 6 members)
###     version 1.1: adding support for 9 members
###     version 1.2: compacting script
###	version 1.3: supporting autodeploy IMC
###     version 2.0: Changed to deploy with only one 'main' menu
###	Version 2.1: Bugfixes
###	Version 2.2: added "How to use the script"
###	Version 2.3: Changed SNMP Community to support iMC version 7.2
###			imc_snmpread = 'iMCV5read' -> 'iMCread'
###			imc_snmpwrite = 'iMCV5write' -> 'iMCwrite'
###	Version 2.4: Supporting latest firmware
###	Version 2.5: Adding optional files to download to the switch
###

###	How to use de script;
###	1) On the HP IMC server(or other tftp-srver), put this script in the "%IMC Install Folder%\server\tmp" folder.
###	2) Set the DHCP-Server in the "deploy" network with this script as bootfile. Example on a Comware devices below.
###			dhcp enable
###			dhcp server forbid 10.0.1.1 10.0.1.200
###			dhcp server ip-pool v1
### 			gateway 10.0.1.1
### 			bootfile-name 5130_irf-config.py
### 			tftp-server ip 10.0.1.100
### 			network 10.0.1.0 24
###	3) Boot a switch without a config-file and connect it to the "deploy" network.

###     I build this script to support additional members when auto-deploying HP5130-PoE-switches with HP iMC.

###	Why ?
###     Normally when deploying the first member of an IRF-stack with HP iMC, the switch is always added as a managed device in HP iMC.
###     Then if you want to auto-deploy another "member" of the same stack this procedure is failing, because it's already added in iMC...

###     In this script I give you the choice for updating switch-software, poe-software and the changing IRF-member-ID.
###     It also support the different member-deploy-scenarios by chosing between the IRF-port-config or iMC-auto-deploy.

###	EXAMPLE:
###        Current Switch Model         48 Ports
###        Current Software version     H3C Comware Software, Version 7.1.059, Alpha 7159
###        Current PoE version          Version 143
###        Current Member ID            1
###        New Member ID                5

###        1.Update Switch Firmware                           [ X ]
###        2.Update PoE Firmware                              [ X ]
###        3.Change IRF MemberID Only                         [ X ]
###        4.Change IRF MemberID and set IRF-Port-config      [   ]
###        5.Trigger iMC for deployment                       [ X ]
###        6.Run selection
###        7.Exit/Quit and reboot

###     For faster deploy the IRF-Port-config is configured by a custom value, see settings below

###          48 Ports IRF-Config
###                  IRF Port  Interface                             
###                  1         Ten-GigabitEthernetX/0/49     (irf_48_port_1)       
###                  2         Ten-GigabitEthernetX/0/51     (irf_48_port_2)        
###          24 Ports IRF-Config
###                  IRF Port  Interface                               
###                  1         Ten-GigabitEthernetX/0/25     (irf_24_port_1)      
###                  2         Ten-GigabitEthernetX/0/27     (irf_24_port_2)

### 	You can change this or other custom settings below when needed

#### Custom settings
tftpsrv = "192.168.0.1"
imc_bootfile = "autocfg_startup.cfg"
optional_file1 = "" # "myscript.py" for example
optional_file2 = ""
imc_snmpread = 'iMCread'
imc_snmpwrite = 'iMCwrite'
bootfile = "5130ei-cmw710-boot-r3111p07.bin"
sysfile = "5130ei-cmw710-system-r3111p07.bin"
poefile = "S5130EI-POE-145.bin"
irf_48_port_1 = "/0/49"
irf_48_port_2 = "/0/51"
irf_24_port_1 = "/0/25"
irf_24_port_2 = "/0/27"
poe_pse_numbers = {"1":"4","2":"7","3":"10","4":"13","5":"16","6":"19","7":"22","8":"25","9":"26"}
irf_prio_numbers = {"1":"32","2":"31","3":"30","4":"29","5":"28","6":"27","7":"26","8":"25","9":"24"}

#### Importing python modules
import comware
import sys
import time
import termios

#### RAW user-input module
fd = sys.stdin.fileno();
new = termios.tcgetattr(fd)
new[3] = new[3] | termios.ICANON | termios.ECHO
new[6] [termios.VMIN] = 1
new[6] [termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, new)
termios.tcsendbreak(fd,0)

#### Notification for Starting
print (('\n' * 5) + "Starting script for deploying IRF-config and software on 5130 switches\n"
        "\nPlease wait while getting the current versions and settings...."
        )

#### Getting Current settings and versions
def SwitchInput():
    sys.stdout.write("\r%d%%" % 0)
    sys.stdout.flush()
    #### Get Current IRF Member
    get_memberid = comware.CLI('display irf link', False).get_output()
    for line in get_memberid:
        if 'Member' in line:
            s1 = line.rindex('Member') + 7
            e1 = len(line)
            memberid = line[s1:e1]
    sys.stdout.write("\r%d%%" % 25)
    sys.stdout.flush()
    #### Get SwitchModel
    get_model = comware.CLI('display int ten brief', False).get_output()
    for line in get_model:
        if '/0/28' in line:
            model = "24 Ports"
        if '/0/52' in line:
            model = "48 Ports"
    sys.stdout.write("\r%d%%" % 50)
    sys.stdout.flush()
    #### Get Mac-address
    get_mac_address = comware.CLI('dis device manuinfo | in MAC_ADDRESS', False).get_output()
    for line in get_mac_address:
        if 'MAC_ADDRESS' in line:
            s2 = line.rindex('MAC_ADDRESS') + 23
            e2 = len(line)
            mac_address = line[s2:e2]
    #### Get Switch Software Version
    get_sw_version = comware.CLI('display version | in Software', False).get_output()
    sw_version = get_sw_version[1]
    sys.stdout.write("\r%d%%" % 75)
    sys.stdout.flush()
    #### Get PoE Software Version
    try:
        comware.CLI('system ; poe enable pse ' + str(poe_pse_numbers[memberid]), False).get_output()
    except SystemError:
        poe_version = 'N/A'
    try:
        comware.CLI('system ; int gig' + memberid + '/0/1 ; poe enable ', False).get_output()
    except SystemError:
        poe_version = 'N/A'
    try:
        get_poe_version = comware.CLI('display poe pse | in Software', False).get_output()
        for line in get_poe_version:
            if 'Software' in line:
                s3 = line.rindex('Software') + 31
                e3 = len(line)
                poe_version = line[s3:e3]
    except SystemError:
        poe_version = 'N/A'
    sys.stdout.write("\r%d%%\n" % 100)
    sys.stdout.flush()
    return memberid, model, mac_address, sw_version, poe_version


#### Startmenu for deploying the switch
def StartMenu(memberid, model, mac_address, sw_version, poe_version):
    checkbox1 = checkbox2 = checkbox3 = checkbox4 = checkbox5 = checkbox6 = set_memberid = ''
    Menu = True
    while Menu:
        print   "\n" * 5 + "Current switch information:",\
                "\n  Current switch model         " + str(model),\
                "\n  Current MAC-address          " + str(mac_address),\
                "\n  Current software version     " + str(sw_version),\
                "\n  Current PoE version          " + str(poe_version),\
                "\n  Current Member-ID            " + str(memberid),\
                "\n  Newly chosen Member-ID       " + str(set_memberid),\
                "\n" * 2 + "Files ready for installation:",\
                "\n  Switch Boot-file             " + str(bootfile),\
                "\n  Switch System-file           " + str(sysfile),\
                "\n  Switch PoE software-file     " + str(poefile),\
                "\n" * 2 + "%-50s %-1s %-1s %-1s" % ("1.Update switch firmware", "[", checkbox1, "]"),\
                "\n%-50s %-1s %-1s %-1s" % ("2.Update PoE firmware", "[", checkbox2, "]"),\
                "\n%-50s %-1s %-1s %-1s" % ("3.Download optional files", "[", checkbox3, "]"),\
                "\n%-50s %-1s %-1s %-1s" % ("4.Change IRF Member-ID only", "[", checkbox4, "]"),\
                "\n%-50s %-1s %-1s %-1s" % ("5.Change IRF Member-ID and set IRF-port-config", "[", checkbox5, "]"),\
                "\n%-50s %-1s %-1s %-1s" % ("6.Trigger iMC for deployment", "[", checkbox6, "]"),\
                "\n%-50s " % ("7.Run selection"),\
                "\n%-50s " % ("8.Exit/Quit and start CLI"),\
                "\n%-50s " % ("9.Exit/Quit and reboot")
        ans=raw_input("\nWhat would you like to do? ")
        if ans=="1":
            checkbox1 = "X"
        elif ans=="2":
            checkbox2 = "X"
        elif ans=="3":
            checkbox3 = "X"
        elif ans=="4":
            set_memberid = raw_input("Enter new Member-ID: ")
            checkbox4 = "X"
        elif ans=="5":
            set_memberid = raw_input("Enter new Member-ID: ")
            checkbox4 = "X"
            checkbox5 = "X"
            checkbox6 = ""
        elif ans=="6":
            checkbox5 = ""
            checkbox6 = "X"
        elif ans=="7":
            Menu = False
        elif ans=="8":
            print "\nQuiting script, starting CLI...\n"
            sys.exit()
        elif ans=="9":
            print "\nQuiting script and rebooting...\n"
            comware.CLI("reboot force")
            sys.exit()
        else:
            print("\n Not Valid Choice Try again")
    return checkbox1, checkbox2, checkbox3, checkbox4, checkbox5, checkbox6 ,set_memberid

#### Switch software update
def SoftwareUpdate(checkbox1):
    if checkbox1 == "X":
        print "\nUpdating Switch Firmware....\n"
        try:
            comware.CLI("tftp " + tftpsrv + " get " + bootfile)
            print "\nSwitch Firmware download successful\n"
        except SystemError as s:
            print "\nSwitch Firmware download successful\n"
        try:
            comware.CLI("tftp " + tftpsrv + " get " + sysfile)
            print "\nSwitch Firmware download successful\n"
        except SystemError as s:
            print "\nSwitch Firmware download successful\n"
        try:
            comware.CLI("boot-loader file boot flash:/" + bootfile + " system flash:/" + sysfile + " all main")
            print "\nConfiguring boot-loader successful\n"
        except SystemError as s:
            print "\nChange bootloader successful\n"
    else:
        print "\nSkipping Switch Firmware update"

#### Switch poe update
def PoEUpdate(checkbox2, memberid):
    if checkbox2 == 'X':
        print "\nUpdating PoE Firmware....\n"
        try:
            comware.CLI("tftp " + tftpsrv + " get " + poefile)
            print "\nPoE Firmware download successful\n"
        except SystemError as s:
            print "\nPoE Firmware download successful\n"
        try:
            print "\nUpdating PoE Firmware..."
            comware.CLI("system ; poe update full " + poefile + " pse " + str(poe_pse_numbers[memberid]))
            print "\nPoE-Update successful\n"
        except SystemError as s:
            print "\nSkipping PoE-Update, member not available\n"
    else:
        print "\nSkipping PoE firmware update"


#### Download optional files

def OptFiles(checkbox3):
    if checkbox3 == 'X':
        print "\nDownloading optional files..."
        if optional_file1:
            comware.CLI('tftp ' + tftpsrv + ' get ' + optional_file1)
        if optional_file2:
            comware.CLI('tftp ' + tftpsrv + ' get ' + optional_file2)
    else:
        print "\nSkipping optional files"

#### Change IRF MemberID
def ChangeIRFMemberID(memberid, checkbox4, set_memberid):
    if checkbox4 == 'X':
        print "\nChanging IRF MemberID..."
        comware.CLI("system ; irf member " + memberid + " renumber " + set_memberid)
    else:
        print "\nskipping IRF MemberID Change"


#### Set IRFPorts in startup config
def SetIRFPorts(memberid, model, checkbox5, set_memberid):
    if checkbox5 == 'X':
        if model == "48 Ports":
            print ('\n' * 5) + 'Deploying IRF-Port-config for 48 ports switch...\n'
        if model == "24 Ports":
            print ('\n' * 5) + 'Deploying IRF-Port-config for 24 ports switch...\n'
        set_prio = irf_prio_numbers[set_memberid]
        startup_file = open('flash:/startup.cfg', 'w')
        startup_file.write("\nirf member "+ set_memberid +" priority "+ set_prio + "\n")
        if model == "48 Ports":
            startup_file.write("\nirf-port "+ set_memberid +"/1")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_48_port_1 + '\n')
            startup_file.write("\nirf-port "+ set_memberid +"/2")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_48_port_2 + '\n')
        if model == "24 Ports":
            startup_file.write("\nirf-port "+ set_memberid +"/1")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_24_port_1 + '\n')
            startup_file.write("\nirf-port "+ set_memberid +"/2")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_24_port_2 + '\n')
        startup_file.close()
        comware.CLI("startup saved-configuration startup.cfg")
    else:
        print "\nSkipping IRF-Port-config"

#### Trigger iMC for auto-deployment
def TriggeriMC(checkbox6):
    if checkbox6 == 'X':
        print "\nTriggering iMC for deploy, please wait..."
        comware.CLI('system ; snmp-agent ; snmp-agent community read ' + imc_snmpread + ' ; snmp-agent community write ' + imc_snmpwrite + ' ; snmp-agent sys-info version all', False)
        comware.CLI('tftp ' + tftpsrv + ' get ' + imc_bootfile + ' tmp.cfg')
        for s in range(300):
                sys.stdout.write("\r%s%s%s" % ("iMC Triggered successfully, waiting for config...", str(300 - s), " seconds remaining"))
                sys.stdout.flush()
                time.sleep( 1 )
    else:
        print "\nSkipping iMC deploy"

#### Reboot in 10 Seconds
def Reboot():
        for s in range(10):
            sys.stdout.write("\r%s%s%s" % ("Rebooting in: ", str(10 - s), " seconds..."))
            sys.stdout.flush()
            time.sleep( 1 )
        print "Now rebooting, please wait..."
        comware.CLI("reboot force", False)

#### Define main function
def main():
    try:
        (memberid, model, mac_address, sw_version, poe_version) = SwitchInput()
        (checkbox1, checkbox2, checkbox3, checkbox4, checkbox5, checkbox6 ,set_memberid) = StartMenu(memberid, model, mac_address, sw_version, poe_version)
        SoftwareUpdate(checkbox1)
        PoEUpdate(checkbox2, memberid)
        OptFiles(checkbox3)
        ChangeIRFMemberID(memberid, checkbox4, set_memberid)
        SetIRFPorts(memberid, model, checkbox5, set_memberid)
        TriggeriMC(checkbox6)
        Reboot()
    except (EOFError, KeyboardInterrupt):
        print "\n\nquiting script!!!...."
        quit()

if __name__ == "__main__":
    main()

