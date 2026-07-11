# Experimental ERC-4337 Bundler Setup - Fast Track

The following steps assume two machines:

1. The server where Anvil and Alto will run, and power consumption will be measured using SmartWatts
2. A client machine (preferably a VM on the server), which will be used as control plane for starting the services on the server and to run the tests.

This fast track setup assumes a pre-deployment of all needed contracts: EntryPoint, the smart accounts factory contract, an ERC-20 token contract, a set of smart contract accounts (SCAs). Also the SCAs are pre-funded with both Ether (for paying transactions' cost) and ERC-20 tokens (for transferring in the effective transaction load). This pre-deployment is provided in the state.json file, loaded by Anvil. It is recommended to back this up periodically, because running the tests results in persistent changes and increases the file size. 

## Setup the server contents 

Copy the *powerexp* folder on the server's */opt/* directory (use other path if prefered, but this might be present in some scripts).

## Build the docker images on the server

Both Anvil and Alto can be run in Docker containers. This can provide portability, and allows measuring the power consumption at container level granularity (albeit including as the container overhead). 
The prerequisite for this is the installation of [Docker Engine](https://docs.docker.com/engine/install/) on the test machine.
Following a Docker network should be set up to permit the Anvil-Alto intercommunication:\
`docker network create aa-exp || true`\
Using the following configuration, this will let Alto reach Anvil as *http://anvil:8545*.

For building the necessary Docker images, two Dockerfiles are provided in the respective folders in the repository for Anvil and Alto, respectively.
An effective clean build is executed as follows in the folder hosting the Dockerfile:\
`docker build --no-cache --progress=plain -t anvil-debian-slim:local -f AnvilDockerfile .`

The build is similar to Anvil, executing the following in the folder hosting the Dockerfile:\
`docker build --no-cache --progress=plain -t alto-debian-slim:local -f AltoDockerfile .`

Running as above, both Anvil and Alto expose the ports, and are accessible directly on the IP address of the host running the Docker containers. 

## Install SmartWatts on the server

First, check if your system is compatible with the RAPL sensor requirements stated on the SmartWatts/PowerAPI kit website.\
Then, be sure to have the PowerAPI/SmartWatts kit installed. In particular, the following are necessary:\

`docker pull ghcr.io/powerapi-ng/hwpc-sensor`\
`sudo modprobe msr`

For the SmartWatts analysis API the following installation is required (use sudo if necessary):

`apt install -y python3 python3-pip python3-venv python3-dev build-essential`\
`mkdir -p /opt/powerexp/venvs`\
`python3 -m venv /opt/powerexp/venvs/smartwatts`\
`source /opt/powerexp/venvs/smartwatts/bin/activate`\
`pip install smartwatts`\
`pip install "powerapi[hwpc,csv]"`\
`deactivate`

*Note:* The *powerexp/results/config_file.json* includes the configuration for the power consumption measurement. This is hardware architecture dependent. 
It should be checked if the configuration complies with the Group Events in the Usage section here: https://powerapi.org/reference/sensors/hwpc-sensor/ and adapted accordingly (rapl, msr and core events).\
Similarly, the *powerexp/results/process.sh* includes two arguments for the smartwatts call that are hardware architecture dependent: *--cpu-base-freq* and *--cpu-tdp*. These should be changed accordingly to the CPU characteristics on the test host.   

## Setup the client machine

Copy the *test_scripts* folder on the client machine. 

Install [node.js](https://nodejs.org/en/download) on the client machine.\
Additional prerequisites might be needed, e.g.,`npm install typescript` and `npm install --save-dev @types/node`. The full package information is available in *package.json*. 

In the .ts scripts replace the localhost address with the server address.

The script has various hardcoded parameters that can be configured, like:

- the number and addresses of the SCAs (loaded from the *created_accounts_salt_0x0A.json* file)
- the throttle time per round of messages
- the total number of rounds

Note: In the *test_scripts* folder there is a *helper_scripts* folder. This includes several bash scripts, which normally should not be required, but could be used for creating smart contract accounts and financing these. Also the current repo includes a contracts folder, which holds the source for the ERC-20 token. This is already deployed on the state that was copied in the above steps on the server. 

## Run the test workflow

The test workflow is included in *runTests.sh*. This first transpiles the .ts scripts to .js.\
Then it starts the Anvil and Alto docker containers on the server and their power consumption monitoring (*measure.sh*).\ 
This is executed via ssh, which should be configured to access the server (change server_host to the server address and provide an authentication, via password or private/public key).\
The UserOps load is afterwards sent from the client machine by running the *transferUserOpRoundsThrottled.js* .\
The confirmed blocks and their timestamps are logged on the client machine. The log is uploaded to the server via scp to be packed with the rest of the measurements when the experiment ends (this also requires changing server_host to the proper address and provisioning an authentication as above).\ 
Finally, the containers are stopped and another script is executed on the server (*process.sh*), to process the resulting measurements and pack these into a *smart_watts.tar.gz* file.
This file includes the data for plotting and should be fetched from the server.




