from setuptools import find_packages, setup

package_name = 'my_robot_voltage'

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
    maintainer='Amaya',
    maintainer_email='amaya.olivas@student.nmt.edu',
    description='Voltage node, reads voltage data to send to GUI',
    license='Apache 2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'voltage_node = my_robot_voltage.voltage_node:main',
        ],
    },
)
