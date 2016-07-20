# Auto-config a port when connecting an HPE UWW-AP to a Comware7 Switch
#
#-------------------------------------------------------------------------------------
# Author:      Remi Batist
# Version:     1.1
#
# Created:     31-03-2016
# Comments:    remi.batist@axez.nl
#
# Modified by:  Wade Wells HPE July 20 2016 for use with UWW (comware based) Access Points
# Comments:     Everything beyond the HP 560 and 525s is an educated guess (in regard
#               to lldp neighbor-info response).  The syntax for other models may need
#               to be tweaked in the uww_ap_array for other models.  
#
#               AP Models Currently accounted for in uww_ap_array (AM, IL, JP, WW):
#               417, 425, MSM430, MSM460, MSM466, MSM466-R, 525, 527, 560
#
# UWW Version:  1.0
#  >> Use at own risk, with this and any script recommend testing in non-production first <<
#-------------------------------------------------------------------------------------
#
# Pushing config every 5 minutes when AP detected with LLDP
# Removing config at 23:00 (when port with description UWW-AP is down)

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
# always start with 'default' and end with 'poe enable' in the ap-config!

# uww_ap_array contains all possible UWW AP models
uww_ap_array = ['HP 417-AM', 'HP 417-IL', 'HP 417-JP', 'HP 417-WW', 'HP 425-AM', 'HP 425-IL', 'HP 425-JP', 'HP 425-WW', 'HP MSM430-AM', 'HP MSM430-IL', 'HP MSM430-JP', 'HP MSM430-WW', 'HP MSM460-AM', 'HP MSM460-IL', 'HP MSM460-JP', 'HP MSM460-WW', 'HP MSM466-AM', 'HP MSM466-IL', 'HP MSM466-JP', 'HP MSM466-WW', 'HP MSM466-R-AM', 'HP MSM466-R-IL', 'HP MSM466-R-JP', 'HP MSM466-R-WW', 'HP 525-AM', 'HP 525-IL', 'HP 525-JP', 'HP 525-WW', 'HP 527-AM', 'HP 527-IL', 'HP 527-JP', 'HP 527-WW', 'HP 560-AM', 'HP 560-IL', 'HP 560-JP', 'HP 560-WW']
ap_config_part1 =   "\ndefault" \
                    "\nport link-type trunk"\
                    "\nundo port trunk permit vlan 1"\
                    "\nport trunk permit vlan 30 110 101 to 103"\
                    "\nport trunk pvid vlan 30"\
                    "\npoe enable"  
ap_config_part2 =   ""

default_config_part1 =  "\ndefault" \
                        "\ndescription pc-port" \
                        "\nport access vlan 30" \
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
            for ap in uww_ap_array:
                if 'System description  : HP Comware Platform Software ' + ap in line:
                    print 'AP found at port ' + port
                    brief = comware.CLI('display interface ' + port + ' brief', False).get_output()
                    if not 'UWW-AP' in str(brief):
                        if ap_config_part1:
                            print 'Applying AP Configuration to ' + port
                            comware.CLI('system-view ; interface ' + port + ' ; ' + ap_config_part1 +' ; return ; ', False)
                        if ap_config_part2:
                            comware.CLI('system-view ; interface ' + port + ' ; ' + ap_config_part2 +' ; return ; ', False)
                        comware.CLI('system-view ; interface ' + port + ' ; description UWW-AP ; return ; ', False)
                    else:
					    print 'AP Configuration Already Applied to ' + port + ' Nothing to do here.'

    elif argument == "remove":
        result = comware.CLI('display interface brief', False).get_output()
        port = ''
        for line in result:
            if 'DOWN' in line and 'UWW-AP' in line:
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
	config(sys.argv[1])


