# Stretch Robot

Stretch robot control code

## Getting Started

> These instructions have only been successfully tested on a Linux machine. They were also tested on a Mac M1 machine, but support for `librealsense` on non-X86 devices is pretty bad at the moment.

1. Create a Conda environment:

```bash
conda create --name stretch python=3.10
```

2. Install pre-requisites:

```bash
# Required installation tools
conda install -c conda-forge ffmpeg cmake librealsense

# Code formatting tools
conda install cmake-format clang-format
```

4. Install the package:

```bash
make install
```

5. Prepare frontend:

```bash
cd stretch/frontend
nvm use 16.15.1
npm install
```

6. Run the bot:

```bash
bot
```

## References

- Hello Robot repositories
  - [Stretch Body](https://github.com/hello-robot/stretch_body)
  - [Stretch Firmware](https://github.com/hello-robot/stretch_firmware)
  - [Stretch ROS](https://github.com/hello-robot/stretch_ros)
