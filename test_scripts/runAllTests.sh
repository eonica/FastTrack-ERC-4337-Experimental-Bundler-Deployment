#!/usr/bin/env bash
set -euo pipefail

echo "Dockerized Tests"

echo "Test#1 50 rounds; 100 SCA(UserOps); 25 throttle"
./runTests 100 25 1

echo "Test#2 50 rounds; 100 SCA(UserOps); 50 throttle"
./runTests 100 50 50 

echo "Test#3 50 rounds; 100 SCA(UserOps); 100 throttle"
./runTests 100 100 50 

echo "Test#4 50 rounds; 75 SCA(UserOps); 25 throttle"
./runTests 75 25 50 

echo "Test#5 50 rounds; 50 SCA(UserOps); 25 throttle"
./runTests 50 25 50 

echo "Test#6 50 rounds; 25 SCA(UserOps); 25 throttle"
./runTests 25 25 50 

echo "Test#7 100 rounds; 100 SCA(UserOps); 25 throttle; Block time 6 seconds"
./runTests 100 25 50 6

echo "Test#8 300 rounds; 100 SCA(UserOps); 25 throttle; Block time 2 seconds"
./runTests 100 25 50 2

echo "Test#9 runIdleTest for idle measurement (no UserOps processing)"
./runIdleTest
