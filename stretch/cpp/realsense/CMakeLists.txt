set(LIBRARY_NAME lib)

# Adds third-party packages.
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/third_party)

# Gets all source files.
file(GLOB_RECURSE SRC_FILES *.c *.cpp)

find_library(ATOMIC_LIBRARY NAMES atomic libatomic latomic)

# RealSense external repository.
include(ExternalProject)
ExternalProject_Add(
  realsense2
  GIT_REPOSITORY "git@github.com:IntelRealSense/librealsense.git"
  GIT_TAG master
  UPDATE_COMMAND ""
  INSTALL_COMMAND ""
  CMAKE_ARGS -DCMAKE_OSX_ARCHITECTURES=arm64
             -DCMAKE_THREAD_LIBS_INIT=-lpthread
             -DCMAKE_BUILD_TYPE=RELEASE
             -DBUILD_NETWORK_DEVICE=OFF
             -DBUILD_SHARED_LIBS=ON
             -DBUILD_EXAMPLES=OFF
             -DBUILD_WITH_OPENMP=OFF
             -DHWM_OVER_XU=OFF
             -DCMAKE_C_STANDARD=11
             -DCMAKE_CXX_STANDARD=11
             -DCMAKE_CXX_STANDARD_REQUIRED=TRUE)

find_package(PythonLibs REQUIRED)
find_package(pybind11 REQUIRED)

# Links relevant directories.
link_directories(${TORCH_INSTALL_PREFIX}/lib)
if(DEFINED ENV{CONDA_PREFIX})
  link_directories($ENV{CONDA_PREFIX}/lib)
endif()

add_library(${LIBRARY_NAME} SHARED ${SRC_FILES})
add_dependencies(${LIBRARY_NAME} realsense2)

# Sets shared library properties.
set_target_properties(${LIBRARY_NAME} PROPERTIES LIBRARY_OUTPUT_DIRECTORY
                                                 ${CMAKE_CURRENT_SOURCE_DIR})
set_target_properties(${LIBRARY_NAME} PROPERTIES PREFIX "")
set_target_properties(${LIBRARY_NAME} PROPERTIES OUTPUT_NAME ${LIBRARY_NAME})

# Links with Torch directories.
target_include_directories(
  ${LIBRARY_NAME}
  PUBLIC ${PYTHON_INCLUDE_DIRS}
  PUBLIC ${pybind11_INCLUDE_DIRS})
target_link_libraries(
  ${LIBRARY_NAME}
  PUBLIC ${pybind11_LIBRARIES}
  PUBLIC ${realsense2_LIBRARY})
