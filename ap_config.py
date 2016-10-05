# Auto-config a port when connecting an Aruba-AP to a Comware7 Switch
#
#------------------------------------------------------------------------------------
# Author:      Remi Batist / AXEZ ICT Solutions
# Version:     1.2
#
# Created:     16-08-2016
# Comments:    remi.batist@axez.nl
#
# Use at own risk, with this and any script recommend testing in non-production first
#------------------------------------------------------------------------------------
#
# Pushing config every 5 minutes when AP detected with LLDP
# Removing config at 23:00 (when port with description ARUBA-AP is down)

# To configure on the comware switch:

# scheduler job AP-DEPLOY
#  command 1 python ap_config.py deploy
#
# scheduler job AP-REMOVE
#  command 1 python ap_config.py remove
#
# scheduler schedule AP-DEPLOY
#  user-role network-admin
#  job AP-DEPLOY
#  time repeating interval 5
#
# scheduler schedule AP-REMOVE
#  user-role network-admin
#  job AP-REMOVE
#  time repeating at 23:00

import comware
import sys

# Support for max 9 lines per config-part
# always start with 'default' and end with 'poe enable' in the ap-config!

ap_config_part1 =   "\ndefault" \
                    "\nport link-type trunk"\
                    "\nundo port trunk permit vlan 1"\
                    "\nport trunk permit vlan 21 40 to 45"\
                    "\nport trunk pvid vlan 21"\
                    "\npoe enable"
ap_config_part2 =   ""

default_config_part1 =  "\ndefault" \
                        "\ndescription vi-access-port" \
                        "\nundo enable snmp trap updown" \
                        "\nport link-type hybrid" \
                        "\nport hybrid vlan 1 untagged" \
                        "\nmac-vlan enable" \
                        "\npoe enable" \
                        "\nundo dot1x handshake"

default_config_part2 =  "\nundo dot1x multicast-trigger" \
                        "\ndot1x critical vlan 666" \
                        "\ndot1x re-authenticate server-unreachable keep-online" \
                        "\nmac-authentication re-authenticate server-unreachable keep-online" \
                        "\nmac-authentication guest-vlan 36" \
                        "\nmac-authentication guest-vlan auth-period 300" \
                        "\nmac-authentication critical vlan 666" \
                        "\nport-security port-mode userlogin-secure-or-mac-ext" \
                        "\nloopback-detection action shutdown"

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
                print 'AP found at port ' + port
                brief = comware.CLI('display interface ' + port + ' brief', False).get_output()
                if not 'ARUBA-AP' in str(brief):
                    if ap_config_part1:
                        print 'Applying defined AP Configuration to port...'
                        comware.CLI('system-view ; interface ' + port + ' ; ' + ap_config_part1 +' ; return ; ', False)
                    if ap_config_part2:
                        comware.CLI('system-view ; interface ' + port + ' ; ' + ap_config_part2 +' ; return ; ', False)
                    comware.CLI('system-view ; interface ' + port + ' ; description ARUBA-AP ; return ; ', False)
                else:
				    print 'AP Configuration Already Applied to ' + port + ' Nothing to do here.'

    elif argument == "remove":
        result = comware.CLI('display interface brief', False).get_output()
        port = ''
        for line in result:
            if 'DOWN' in line and 'ARUBA-AP' in line:
                start = line.rindex('GE') + 2
                end = line.rindex('GE') + 8
                port = 'GigabitEthernet' + line[start:end]
                if default_config_part1:
                    print 'AP at ' + port + ' is down, applying defined default configuration to port...'
                    comware.CLI('system-view ; interface ' + port + ' ; ' + default_config_part1 + ' ; return ; ', False)
                if default_config_part2:
                    comware.CLI('system-view ; interface ' + port + ' ; ' + default_config_part2 + ' ; return ; ', False)

    else:
        print   "\nEnter the right arguments!" \
                "\n   -> ap_config.py deploy" \
                "\n   -> ap_config.py remove"


if __name__ == "__main__":
    try:
        config(sys.argv[1])
    except:
        print   "\nEnter the right arguments!!" \
                "\n   -> ap_config.py deploy" \
                "\n   -> ap_config.py remove"




