from setuptools import find_packages, setup

package_name = 'panda_sim'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='xia',
    maintainer_email='2427815879@qq.com',
    description='Panda MuJoCo simulation, control, and policy nodes for ROS 2',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'sim_node = panda_sim.sim_node:main',
            'state_monitor = panda_sim.state_monitor:main',
            'controller_node = panda_sim.controller_node:main',
            'policy_node = panda_sim.policy_node:main',
        ],
    },
)
