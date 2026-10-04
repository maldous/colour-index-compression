cmake_minimum_required(VERSION 3.21)
project(CIXSDK VERSION 0.1.0 LANGUAGES C)

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)

set(CIX_NATIVE_LIBRARY "" CACHE FILEPATH
    "Path to an already-built libcix_native shared or static library")
if(NOT EXISTS "${CIX_NATIVE_LIBRARY}" OR IS_DIRECTORY "${CIX_NATIVE_LIBRARY}")
    message(FATAL_ERROR "Set CIX_NATIVE_LIBRARY to a selected built libcix_native shared library or Unix static archive")
endif()

get_filename_component(CIX_SOURCE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." REALPATH)
get_filename_component(CIX_NATIVE_LIBRARY_NAME "${CIX_NATIVE_LIBRARY}" NAME)
if(NOT CIX_NATIVE_LIBRARY_NAME MATCHES "^libcix_native\\.(so|dylib|a)$")
    message(FATAL_ERROR "CIX_NATIVE_LIBRARY supports libcix_native.so, libcix_native.dylib, or libcix_native.a only; Windows DLL/import-library pairing is not implemented")
endif()

if(NOT IS_ABSOLUTE "${CMAKE_INSTALL_PREFIX}")
    message(FATAL_ERROR "CMAKE_INSTALL_PREFIX must be absolute for relocatable pkg-config metadata")
endif()
if(IS_ABSOLUTE "${CMAKE_INSTALL_LIBDIR}" OR IS_ABSOLUTE "${CMAKE_INSTALL_INCLUDEDIR}")
    message(FATAL_ERROR "CMAKE_INSTALL_LIBDIR and CMAKE_INSTALL_INCLUDEDIR must be prefix-relative")
endif()
set(CIX_PC_INSTALL_DIRECTORY "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/pkgconfig")
file(RELATIVE_PATH CIX_PC_DIRECTORY_WITHIN_PREFIX
    "${CMAKE_INSTALL_PREFIX}" "${CIX_PC_INSTALL_DIRECTORY}")
if(CIX_PC_DIRECTORY_WITHIN_PREFIX MATCHES "^\\.\\.")
    message(FATAL_ERROR "CMAKE_INSTALL_LIBDIR must remain beneath CMAKE_INSTALL_PREFIX")
endif()
file(RELATIVE_PATH CIX_PC_PREFIX_FROM_PCDIR
    "${CIX_PC_INSTALL_DIRECTORY}" "${CMAKE_INSTALL_PREFIX}")

set(CIX_SDK_CONFIG_DIR "${CMAKE_INSTALL_LIBDIR}/cmake/CIX")
configure_package_config_file(
    "${CMAKE_CURRENT_LIST_DIR}/CIXConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/CIXConfig.cmake"
    INSTALL_DESTINATION "${CIX_SDK_CONFIG_DIR}"
    PATH_VARS CMAKE_INSTALL_INCLUDEDIR CMAKE_INSTALL_LIBDIR)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/CIXConfigVersion.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMajorVersion)
configure_file("${CMAKE_CURRENT_LIST_DIR}/cix.pc.in"
               "${CMAKE_CURRENT_BINARY_DIR}/cix-native.pc" @ONLY)

install(FILES
    "${CIX_SOURCE_ROOT}/include/cix.h"
    "${CIX_SOURCE_ROOT}/include/cix.hpp"
    "${CIX_SOURCE_ROOT}/include/cix_stream.h"
    "${CIX_SOURCE_ROOT}/include/cix_formats.h"
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")
install(FILES "${CIX_NATIVE_LIBRARY}" DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/CIXConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/CIXConfigVersion.cmake"
    DESTINATION "${CIX_SDK_CONFIG_DIR}")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/cix-native.pc"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/pkgconfig")
install(FILES "${CMAKE_CURRENT_LIST_DIR}/README.md"
    DESTINATION "${CMAKE_INSTALL_DOCDIR}")
