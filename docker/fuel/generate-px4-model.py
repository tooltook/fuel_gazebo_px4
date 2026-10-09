#!/usr/bin/env python3
"""Generate PX4 Iris with FUEL sensors and scenes without the ideal drone."""
from pathlib import Path
import copy
import subprocess
import sys
import xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[2]
sim=root/'PX4-Autopilot/Tools/simulation/gazebo-classic/sitl_gazebo-classic'
pkg=root/'fuel_ws/src/fuel_gazebo'
out=pkg/'generated';out.mkdir(exist_ok=True)
subprocess.run([sys.executable,str(sim/'scripts/jinja_gen.py'),str(sim/'models/iris/iris.sdf.jinja'),str(sim),'--output-file',str(out/'iris_base.sdf')],check=True)
tree=ET.parse(out/'iris_base.sdf');model=tree.getroot().find('model');body=model.find("link[@name='base_link']")
source=ET.parse(pkg/'worlds/fuel_room.world').getroot().find("world/model[@name='fuel_drone']/link[@name='body']")
for sensor in source.findall('sensor'):
    item=copy.deepcopy(sensor);item.find('pose').text='0.35 0 0.15 0 0 0';body.append(item)
model.append(ET.fromstring('''<plugin name="fuel_ground_truth" filename="libgazebo_ros_p3d.so">
 <robotNamespace>/gazebo_fuel</robotNamespace><bodyName>base_link</bodyName><topicName>ground_truth</topicName>
 <frameName>world</frameName><updateRate>100</updateRate><gaussianNoise>0</gaussianNoise>
 <xyzOffset>0 0 0</xyzOffset><rpyOffset>0 0 0</rpyOffset>
</plugin>'''))
tree.write(out/'iris_fuel.sdf',encoding='utf-8',xml_declaration=True)
for scene,filename in [('simple','fuel_room.world'),('complex','fuel_complex.world')]:
    tree=ET.parse(pkg/'worlds'/filename);world=tree.getroot().find('world')
    world.remove(world.find("model[@name='fuel_drone']"));world.set('name','px4_'+scene)
    tree.write(out/f'px4_{scene}.world',encoding='utf-8',xml_declaration=True)
print('Generated Iris sensors and PX4 worlds:',out)

# Generated runtime startup hook, applied before EKF2 starts (height source needs restart).
params=root/'PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.params'
marker='# FUEL localization configuration'
base=params.read_text().split(marker)[0].rstrip()
params.write_text(base+"\n"+marker+"\n"+"""if [ "$FUEL_LOCALIZATION" = "sim_vision" ]; then
 param set EKF2_GPS_CTRL 0
 param set EKF2_HGT_REF 3
 param set EKF2_EV_CTRL 11
 param set EKF2_BARO_CTRL 0
 param set EKF2_MAG_TYPE 5
 param set EKF2_EV_DELAY 0
 param set EKF2_EVP_NOISE 0.05
 param set COM_ARM_WO_GPS 1
else
 param set EKF2_GPS_CTRL 7
 param set EKF2_HGT_REF 1
 param set EKF2_EV_CTRL 0
 param set EKF2_BARO_CTRL 1
 param set EKF2_MAG_TYPE 0
fi
""")
