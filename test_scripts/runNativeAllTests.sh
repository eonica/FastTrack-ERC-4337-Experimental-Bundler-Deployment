#!/usr/bin/env bash
set -euo pipefail

echo "Native Tests"

echo "Test#1 50 rounds; 100 SCA(UserOps); 25 throttle"
./runNativeTests.sh 100 25 50 12 1

echo "Test#2 50 rounds; 100 SCA(UserOps); 50 throttle"
./runNativeTests.sh 100 50 50 12 2

echo "Test#3 50 rounds; 100 SCA(UserOps); 100 throttle"
./runNativeTests.sh 100 100 50 12 3

echo "Test#4 50 rounds; 75 SCA(UserOps); 25 throttle"
./runNativeTests.sh 75 25 50 12 4

echo "Test#5 50 rounds; 50 SCA(UserOps); 25 throttle"
./runNativeTests.sh 50 25 50 12 5

echo "Test#6 50 rounds; 25 SCA(UserOps); 25 throttle"
./runNativeTests.sh 25 25 50 12 6

echo "Test#7 100 rounds; 100 SCA(UserOps); 25 throttle; Block time 6 seconds"
./runNativeTests.sh 100 25 100 6 7

echo "Test#8 300 rounds; 100 SCA(UserOps); 25 throttle; Block time 2 seconds"
./runNativeTests.sh 100 25 300 2 8

echo "Test#9 runIdleTest for idle measurement (no UserOps processing)"
./runNativeIdleTest.sh
