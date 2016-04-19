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
# Pushing config every 5 minutes when AP detected with LLDP
# Removing config at 23:00 (when port with description ARUBA-AP is down)

#To configure on the comware switch:

#scheduler job AP-DEPLOY
# command 1 python ap_config.py deploy
#
#scheduler job AP-REMOVE
# command 1 python ap_config.py remove
#
#scheduler schedule AP-DEPLOY
# user-role network-admin
# job AP-DEPLOY
# time repeating interval 5
#
#scheduler schedule AP-REMOVE
# user-role network-admin
# job AP-REMOVE
# time repeating at 23:00

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



