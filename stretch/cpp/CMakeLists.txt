cmake_minimum_required(VERSION 3.12 FATAL_ERROR)

project(stretch-cpp LANGUAGES C CXX)

# C++ configurations.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED TRUE)

# Shared library settings
if(APPLE)
  set(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
elseif(WIN32)
  message(FATAL_ERROR "Windows is not supported")
endif()

# Subprojects.
add_subdirectory(realsense)
