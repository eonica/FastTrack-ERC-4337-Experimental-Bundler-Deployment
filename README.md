# Experimental ERC-4337 Bundler Setup - Fast Track

The following steps assume two machines:

1. The server where Anvil and Alto will run, and power consumption will be measured using SmartWatts
2. A client machine (preferably a VM on the server), which will be used as control plane for starting the services on the server and to run the tests. 

## Setup the server contents 

Copy the powerexp folder on the server's /opt/ directory.

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

## Setup the client machine

Copy the test_scripts folder on the client machine. 

Install [node.js](https://nodejs.org/en/download) on the client machine.\
Additional prerequisites might be needed, e.g.,`npm install typescript` and `npm install --save-dev @types/node`. The full package information is available in package.json. 

Note: In the test_scripts folder there is a helper_scripts folder. This includes several bash scripts, which normally should not be required, but could be used for creating additional smart contract accounts and financing these. Also the current repo includes a contracts folder, which holds the source for the ERC-20 token. This is already deployed on the state that was copied in the above steps on the server. 



## Run the test workflow
