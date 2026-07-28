#!/usr/bin/env bash
set -euo pipefail

echo "Dockerized Tests"

echo "Test#1 100 SCA(UserOps); 25 throttle; 50 rounds;"
./runTests 100 25 50

echo "Test#2 100 SCA(UserOps); 50 throttle; 50 rounds; " 
./runTests 100 50 50 

echo "Test#3  100 SCA(UserOps); 100 throttle; 50 rounds;"
./runTests 100 100 50 

echo "Test#4  75 SCA(UserOps); 25 throttle; 50 rounds;;"
./runTests 75 25 50 

echo "Test#5 50 SCA(UserOps); 25 throttle; 50 rounds; "
./runTests 50 25 50 

echo "Test#6  25 SCA(UserOps); 25 throttle; 50 rounds;"
./runTests 25 25 50 

echo "Test#7 100 SCA(UserOps); 25 throttle; 100 rounds; Block time 6 seconds"
./runTests 100 25 100 6

echo "Test#8 100 SCA(UserOps); 25 throttle; 300 rounds; Block time 2 seconds"
./runTests 100 25 300 2

echo "Test#9 runIdleTest for idle measurement (no UserOps processing)"
./runIdleTest
