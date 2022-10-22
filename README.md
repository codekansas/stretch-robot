# Stretch Robot

Stretch robot control code

## Getting Started

1. Create a Conda environment:

```bash
conda create --name stretch python=3.8
```

2. Install pre-requisites:

```bash
# Make sure certain C++ dependencies are installed
brew install gcc-12

# Required installation tools
conda install -c conda-forge ffmpeg cmake

# Code formatting tools
conda install cmake-format clang-format
```

4. Install the package:

```bash
make install
```

5. Run the bot:

```bash
bot
```

## References

- Hello Robot repositories
  - [Stretch Body](https://github.com/hello-robot/stretch_body)
  - [Stretch Firmware](https://github.com/hello-robot/stretch_firmware)
  - [Stretch ROS](https://github.com/hello-robot/stretch_ros)
