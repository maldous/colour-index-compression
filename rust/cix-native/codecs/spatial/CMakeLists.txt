cmake_minimum_required(VERSION 3.20)
project(cix_spatial_bridge LANGUAGES CXX)

# Inputs are selected by the distribution build.  The fallback hints cover
# conventional prefix and Debian-style SDK layouts without searching the host.
set(CIX_SPATIAL_ROOT "" CACHE PATH "Provisioned CharLS/OpenJPEG prefix")
set(CIX_CHARLS_LIBRARY "" CACHE FILEPATH "Selected CharLS library in the provisioned prefix")
set(CIX_OPENJPEG_LIBRARY "" CACHE FILEPATH "Selected OpenJPEG library in the provisioned prefix")
if(NOT IS_DIRECTORY "${CIX_SPATIAL_ROOT}")
    message(FATAL_ERROR "Set CIX_SPATIAL_ROOT to the immutable codec SDK prefix")
endif()
set(CIX_SPATIAL_INCLUDE_HINTS
    "${CIX_SPATIAL_ROOT}/include"
    "${CIX_SPATIAL_ROOT}/usr/include")
set(CIX_SPATIAL_LIBRARY_HINTS
    "${CIX_SPATIAL_ROOT}/lib"
    "${CIX_SPATIAL_ROOT}/lib64"
    "${CIX_SPATIAL_ROOT}/usr/lib"
    "${CIX_SPATIAL_ROOT}/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}")
find_path(CIX_CHARLS_INCLUDE charls/charls.h HINTS ${CIX_SPATIAL_INCLUDE_HINTS} NO_DEFAULT_PATH REQUIRED)
find_path(CIX_OPENJPEG_INCLUDE openjpeg.h
    HINTS "${CIX_SPATIAL_ROOT}/include/openjpeg-2.5" "${CIX_SPATIAL_ROOT}/usr/include/openjpeg-2.5"
    NO_DEFAULT_PATH REQUIRED)
if(NOT CIX_CHARLS_LIBRARY)
    # CIX_CHARLS_LIBRARY is an empty cache entry by default. Discover into a
    # separate variable so CMake does not treat that empty cache value as a
    # completed find_library result.
    find_library(CIX_CHARLS_DISCOVERED_LIBRARY NAMES charls CharLS
        HINTS ${CIX_SPATIAL_LIBRARY_HINTS} NO_DEFAULT_PATH REQUIRED)
    set(CIX_CHARLS_LIBRARY "${CIX_CHARLS_DISCOVERED_LIBRARY}")
endif()
if(NOT CIX_OPENJPEG_LIBRARY)
    find_library(CIX_OPENJPEG_DISCOVERED_LIBRARY NAMES openjp2 openjpeg
        HINTS ${CIX_SPATIAL_LIBRARY_HINTS} NO_DEFAULT_PATH REQUIRED)
    set(CIX_OPENJPEG_LIBRARY "${CIX_OPENJPEG_DISCOVERED_LIBRARY}")
endif()
foreach(selected_library IN ITEMS CIX_CHARLS_LIBRARY CIX_OPENJPEG_LIBRARY)
    if(NOT IS_ABSOLUTE "${${selected_library}}" OR NOT EXISTS "${${selected_library}}")
        message(FATAL_ERROR "${selected_library} must be an existing absolute selected codec library")
    endif()
endforeach()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_library(cix_spatial_bridge SHARED cix_spatial_bridge.cpp)
target_compile_definitions(cix_spatial_bridge PRIVATE CIX_SPATIAL_BRIDGE_BUILDING)
target_include_directories(cix_spatial_bridge PRIVATE "${CIX_CHARLS_INCLUDE}" "${CIX_OPENJPEG_INCLUDE}")
target_link_libraries(cix_spatial_bridge PRIVATE "${CIX_CHARLS_LIBRARY}" "${CIX_OPENJPEG_LIBRARY}")
set_target_properties(cix_spatial_bridge PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN YES
    OUTPUT_NAME cix_spatial_bridge)
if(MSVC)
    target_compile_options(cix_spatial_bridge PRIVATE /O2 /fp:strict)
else()
    target_compile_options(cix_spatial_bridge PRIVATE
        -O3 -fno-fast-math -ffp-contract=off -fno-strict-aliasing)
endif()
if(UNIX AND NOT APPLE)
    set_target_properties(cix_spatial_bridge PROPERTIES INSTALL_RPATH "$ORIGIN")
elseif(APPLE)
    set_target_properties(cix_spatial_bridge PROPERTIES INSTALL_RPATH "@loader_path")
endif()
include(GNUInstallDirs)
install(TARGETS cix_spatial_bridge
    LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(FILES cix_spatial_bridge.h DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/cix")
