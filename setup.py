from setuptools import setup, find_packages

setup(
    name='pyudev_programmer',
    version='0.1',
    description='Listen for USB devices and execute commands on hotplug',
    packages=find_packages(exclude=['build', 'dist', '*.egg-info']),
    install_requires=['pyudev'],
    entry_points = {
        'console_scripts':
            ['pyudev_programmer=pyudev_programmer.command_line:main'],
    },
)
