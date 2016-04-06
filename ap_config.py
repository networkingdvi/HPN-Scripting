# Auto-config a port when connecting an Aruba-AP to a Comware7 Switch
#
#-------------------------------------------------------------------------------
# Author:      Remi Batist
# Version:     1.1
#
# Created:     31-03-2016
# Comments:    remi.batist@axez.nl
#-------------------------------------------------------------------------------
#
# --Pushing config when AP detected with LLDP
# --Removing config when AP is removed(PoE stops delivering power)
#
# Put this script on the switch and configure the switch
# To configure on the comware switch:

#rtm cli-policy AP-DEPLOY
# event syslog priority all msg "neighbor created" occurs 1 period 1
# action 0 syslog priority 6 facility local6 msg "starting AP-configuration"
# action 1 cli python ap_config.py deploy
# action 2 syslog priority 6 facility local6 msg "AP-configuration finished"
# running-time 300
# user-role network-admin
# commit

#rtm cli-policy AP-REMOVE
# event syslog priority all msg "Detection Status 1" occurs 1 period 1
# action 0 syslog priority 6 facility local6 msg "deleting AP-configuration"
# action 1 cli python ap_config.py remove
# action 2 syslog priority 6 facility local6 msg "deleting AP-configuration finished"
# running-time 300
# user-role network-admin
# commit

import comware
import sys

# Support for max 6 lines per config-part

ap_config_part1 =   "\ndefault" \
                    "\nport link-type trunk"\
                    "\nundo port trunk permit vlan 1"\
                    "\nport trunk permit vlan 10 20 to 25"\
                    "\nport trunk pvid vlan 10"\
                    "\npoe enable"
ap_config_part2 =   ""

default_config_part1 =  "\ndefault" \
                        "\ndescription pc-port" \
                        "\nport access vlan 5" \
                        "\npoe enable"

default_config_part2 =  ""


def config(argument):
    if argument == "deploy":
        result = comware.CLI('display lldp neighbor-information verbose', False).get_output()
        port = ''
        for line in result:
            if 'LLDP neighbor-information of port' in line:
                start = line.rindex('[') + 1
                end = line.rindex(']', start)
                port = line[start:end]
            if 'System description  : ArubaOS' in line:
                brief = comware.CLI('display interface ' + port + ' brief', False).get_output()
                if not 'ARUBA-AP' in str(brief):
                    if ap_config_part1:
                        comware.CLI('system-view ; interface ' + port + ' ; ' + ap_config_part1 +' ; return ; ', False)
                    if ap_config_part2:
                        comware.CLI('system-view ; interface ' + port + ' ; ' + ap_config_part2 +' ; return ; ', False)
                    comware.CLI('system-view ; interface ' + port + ' ; description ARUBA-AP-PRE ; return ; ', False)
                if 'ARUBA-AP-PRE' in str(brief):
                    comware.CLI('system-view ; interface ' + port + ' ; description ARUBA-AP ; return ; ', False)

    elif argument == "remove":
        result = comware.CLI('display interface brief', False).get_output()
        port = ''
        for line in result:
            if 'DOWN' in line and 'ARUBA-AP' in line:
                start = line.rindex('GE') + 2
                end = line.rindex('GE') + 8
                port = 'GigabitEthernet' + line[start:end]
                if default_config_part1:
                    comware.CLI('system-view ; interface ' + port + ' ; ' + default_config_part1 + ' ; return ; ', False)
                if default_config_part2:
                    comware.CLI('system-view ; interface ' + port + ' ; ' + default_config_part2 + ' ; return ; ', False)

    else:
        print   "\nEnter the right arguments!" \
                "\n   -> ap_config.py deploy" \
                "\n   -> ap_config.py remove"


if __name__ == "__main__":
	config(sys.argv[1])



