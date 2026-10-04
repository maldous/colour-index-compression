cmake_minimum_required(VERSION 3.21)
project(cix_installed_cpp_consumer LANGUAGES CXX)

find_package(CIX 0.1 CONFIG REQUIRED)
add_executable(cix_installed_cpp_consumer cpp_installed_consumer.cpp)
target_link_libraries(cix_installed_cpp_consumer PRIVATE CIX::native)
target_compile_features(cix_installed_cpp_consumer PRIVATE cxx_std_17)
