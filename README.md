# Experimental ERC-4337 Bundler Setup
Experimental setup for ERC-4337 Environment Tests used in ISEEE 2025 paper evaluation of ERC-4337 Bundler Power Consumption

This is a guide for setting up an experimental playground for testing an ERC-4337 bundler.\
It was used for monitoring a bundler for its power consumption in measurements conducted for the work in [An Introductory Study on the Power Consumption Overhead of ERC-4337 Bundlers](https://arxiv.org/abs/2511.16890) ISEEE 2025 paper.\
It simulates a feed of ERC-4337 UserOps for transfering ERC-20 tokens between some sets of addresses, via a Bundler and all the ERC-4337 infrastructure. 

It uses mainly the following tools, which require installation/setup (some indications below):

- (Optional) [Blockscout](https://github.com/blockscout/blockscout) blockchain explorer for monitoring the blocks of processed UserOps
- [Anvil (from the Foundry package)](https://github.com/foundry-rs/foundry?tab=readme-ov-file) as blockchain backend simulator
- [Alto (Pimlico)](https://github.com/pimlicolabs/alto) as the tested ERC-4337 bundler
- [SmartWatts](https://powerapi.org/reference/formulas/smartwatts/) for the power consumption measurements

The current setup assumes running everything on the same machine. Therefore, localhost (127.0.0.1), is often used as address in various scripts. Replace this according to changes.\
In particular, in a server setting, Anvil and Alto, should probably run on the server side, and deployment, transaction sending, and other operations should use the server address. 

## (Optional) Configuration of Blockscout

Blockscout would normally require setting the configurations for *anvil* and *chain id* options, in order to monitor the simulated Anvil chain. These are normally found in the *anvil.yml*, *docker-compose.yml*, *env/common-blockscout.env* files in the Blockscout installation.\ 
The options can normally be set as:\
`ETHEREUM_JSONRPC_VARIANT=anvil`
`CHAIN_ID=1`

Blockscout should be further started together with Anvil, for monitoring the produced blocks. It is recommended to start it before Anvil and stop it after stopping Anvil to avoid desyncing issues. This is typically done via docker compose (start and stop):\
`docker-compose -f anvil.yml up -d`
`docker-compose down -v`
Note that use of Blockscout is optional altogether.\
Update: [Anvil Explorer](https://github.com/sigworld/anvil-explorer) is a less problematic block explorer alternative.

## Running Anvil

To run Anvil as the blockchain simulator, after installing a typical command is as follows (with persistent state storage):\
`anvil --port 8545 --host 0.0.0.0 --chain-id 1337 --block-time 15 --gas-limit 30000000 --gas-price 1 --block-base-fee-per-gas 0 --disable-min-priority-fee --load-state /var/lib/anvil/state.json --dump-state /var/lib/anvil/state.json --disable-code-size-limit`

Parameters can be adjusted upon need. Note that --load-state expects a state file and should be ommitted at first run.\
Also note that TLDR: do not start Anvil with --disable-min-priority-fee when accessing via Remix, but only for scripted interaction.\
The --disable-min-priority-fee option will not work for direct Remix interactions with the Anvil network, since Remix internally will set a priority fee, which is expected to be 0 using this option. However, this option might be necessary later for limiting burst costs when running UserOp loads via alto. 

## Deploying necessary contracts

Running an ERC-4337 environment in a private playground needs the deployment of an ERC-4337 EntryPoint contract and of a factory for smart accounts creation on the local simulated chain. The 0.6 versions of the above contracts can be loaded in [Remix](http://remix.ethereum.org) via the *EPLoader.sol* file provided in this repo - the loaded contracts should be present in the *.deps* dependences tree. These contracts can be compiled and deployed to the Anvil network. Note that further minor adjustment in the sources might be needed in order to acccomodate changes with newer versions, depending on the compiler used.

**Update:** The 0.7 versions of EntryPoint and SimpleAccountFactory are currently the most popular. These can be loaded by simply changing the 0.6 version to 0.7 in the *EPLoader.sol*.

**Note:** To connect Remix to a locally hosted Anvil network for contract deployment, some browsers, e.g., Firefox, might require specifically allowing permissions for the Remix URL to access local network devices. These should be configurable via browser settings.

An ERC-20 token contract, the provided *TestToken.sol*, should also be deployed as final destination for the transactions generated from the UserOps feed. 

After these deployments, a number of smart account contracts (SCAs) should be created to act as the UserOps validators and proxys further to the *TestToken.sol*. These should also be funded to act as sponsors for the transactions, as per the basic ERC-4337 flow.\
A test account address from the set generated by Anvil, is pre-allocated with test Ether, and can create, own and use in parallel multiple SCAs, as long as for each configures a different salt.\
A bash script that does this for the first 10 owner test accounts from Anvil is given in *createAccounts* on this repository. For each owner test account the script will create 10 SCAs. 
This can be changed in the script's source configuration parameters, which also require setting the IP address of the Anvil host and of the SCA SimpleAccountFactory contract.   
Usage is by providing the salt and Ether to transfer (optional), e.g.:\
`createAccounts 0x0A 1ether`\
The addresses of the created SCAs are dumped to a file saved using the naming scheme *created_accounts_salt_${SALT}.txt*, and to a similar .json file, ordered by owner (i.e., first 10 SCAs belong to the first Anvil test address, next 10 to the second Anvil address, and so forth). These SCA addresses should be further included in the UserOps feeding script.

The intended use is to send ERC-20 transfers between SCAs, formed initially as ERC-4337 UserOps, and further executed as transactions within the ERC-4337 UserOp flow. For this purpose SCAs must be funded with:\
a) Ether to pay for the effectively executed transactions (i.e., refund the bundler that initially pays)\
b) ERC-20 tokens to transfer between SCAs

Point a) above is solved at SCA creation by transfering Ether. Further Ether can be transferred running the script\
`sendEtherMulti [txt file with SCA addresses] [Xether]` where X is the Ether value.\
Point b) above is solved by running the script\
`sendTokenMulti [txt file with SCA addresses] [X]` where X is the token units number. Note that the ERC-20 token address must be configured in the script.\
**Note:** All scripts expect 10 SCA recipients per owner Anvil test address, so 100 in total. For tuning these numbers, change the params in the scripts' internal configurations.  

## Runing Alto

The Alto bundler requires adjusting its configuration in *alto-config.json* to match the address of the deployed EntryPoint contract and set some sponsor address private keys for funding from the Anvil generated addressed. A typical configuration looks like this:\
`{
    "rpc-url": "http://127.0.0.1:8545",
    "port": 3000,
    "executor-private-keys": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80,0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d,0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a,0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    "utility-private-key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "entrypoints": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
    "safe-mode": false,
    "enforce-unique-senders-per-bundle": false,
    "max-gas-per-bundle": "30000000",
    "fixed-gas-limit-for-estimation": "30000000",
    "bundler-initial-comission": "0",
    "block-time": 15000,
    "gas-price-bump": "1",
    "log-level": "info"
}`

Running Alto afterwards can be done by:\
`./alto run --config "alto-config.json" --port 3000`

## Encapsulating Anvil and Alto in Docker Containers

Both Anvil and Alto can be run as well in Docker containers. This can provide portability, and allows measuring the power consumption at container level granularity (albeit including as the container overhead). 
The prerequisite for this is the installation of [Docker Engine](https://docs.docker.com/engine/install/) on the test machine.
Following a Docker network should be set up to permit the Anvil-Alto intercommunication:\
`docker network create aa-exp || true`\
Using the following configuration, this will let Alto reach Anvil as *http://anvil:8545*.

For building the necessary Docker images, two Dockerfiles are provided in the respective folders in the repository for Anvil and Alto, respectively.
In case of Anvil, it is required to maintain and map the simulated network state in *state.json* from the local file system to the Docker image (paths should be adapted according to local configuration). An effective clean build is executed as follows in the folder hosting the Dockerfile:\
`docker build --no-cache --progress=plain -t anvil-debian-slim:local -f AnvilDockerfile .`\
For running Anvil under Docker with console output (switch the -it flags to -d for detached mode):\
`docker run --rm -it --name anvil --network aa-exp -v /localhost/path/to/state.json:/var/lib/anvil/state.json -p 8545:8545 anvil-debian-slim:local`

Alto requires loading *alto-config.json* by the Docker image (similarly to above, paths should reflect local configuration). The build is similar to Anvil, executing the following in the folder hosting the Dockerfile:\
`docker build --no-cache --progress=plain -t alto-debian-slim:local -f AltoDockerfile .`\
For running Alto under Docker with console output (switch the -it flags to -d for detached mode):\
`docker run --rm -it --name alto --network aa-exp -p 3000:3000 alto-debian-slim:local`

Running as above, both Anvil and Alto expose the ports, and are accessible directly on the IP address of the host running the Docker containers. 
If run in detached mode, to stop the containers:\
`docker stop anvil|alto`

## Running the UserOps feed

The UserOps feed will perform token transfers between SCAs in rounds, in a back-and-forth manner, where first half of the SCAs will transfer tokens to the second half of the SCAs and the second half to the first half (i.e., for 100 SCAs, 1st SCA will transfer to 100th, the 100th to 1st; 2nd SCA will transfer to the 99th, the 99th to the 2nd, etc.).\
Running the feed is done through code written using the [viem](https://viem.sh/account-abstraction) library. This requires installing [node.js](https://nodejs.org/en/download).\
Additional prerequisites might be needed, e.g.,`npm install typescript' and `npm install --save-dev @types/node`. The full package information is available in package.json. 

The UserOps feed can be run using the *transferUserOpRoundsThrottled.ts* script.\
This should be transpiled first to .js (both current versions provided on repo), using:\
`npx tsc -p ./tsconfig.json`

The script has various hardcoded parameters that can or should be configured, like:

- the Anvil and Alto RPC addresses
- the address of the EntryPoint contract 
- the number and addresses of the SCAs (loaded from the json file generated above)
- the number and addresses of the funding accounts, generated by Anvil (typically fixed)
- the destination ERC-20 token address
- the throttle time per round of messages
- the total number of rounds

To finally run the script, simply:\
`node transferUserOpRoundsThrottled.js`

A simpler testing script for executing just a single UserOp transfer is available in *transferUserOpBasic.ts*.

## Monitoring Power Consumption via SmartWatts

First, check if your system is compatible with the RAPL sensor requirements stated on the SmartWatts/PowerAPI kit website.\
Then, be sure to have the PowerAPI/SmartWatts kit installed. In particular, the following are probably necessary:\
`docker pull ghcr.io/powerapi-ng/hwpc-sensor
sudo /usr/bin/python3 -m pip install "powerapi[hwpc,csv]"
sudo modprobe msr`

Monitoring the power consumption requires two steps:

1. Getting the raw RAPL power measurements
2. Computing the SmartWatts accurately estimated actual power consumption per process

For 1) the monitoring options are set in a *config_file.json*, like the metrics monitored, desired sampling, interval and others, which are described on the PowerAPI page. This must be placed in the directory, where the docker command below is run.\
Then, the monitoring can be started using a command line as follows (pay attention to the docked mapping paths, this will place results in a *sensor_output* folder that should exist in the local directory):

`docker run --rm  --net=host --privileged --pid=host -v /sys:/sys -v /var/lib/docker/containers:/var/lib/docker/containers:ro -v $(pwd)/sensor_output:/tmp/sensor_output -v $(pwd):/srv -v $(pwd)/config_file.json:/config_file.json powerapi/hwpc-sensor --config-file /config_file.json`

In order to capture the monitored consumption per process, the target processes should be run in transient scope units leveraging cgroups separation. These should be normally part of the user.slice. You can check information on their cgroups association using:\
`systemd-cgls
ls /sys/fs/cgroup`

And to effectively run in transient scoped mode:\
`systemd-run --scope --slice=user.slice --unit=anvil anvil --port 8545 --host 0.0.0.0 --chain-id 1337 --block-time 15 --gas-limit 30000000 --gas-price 1 --block-base-fee-per-gas 0 --disable-min-priority-fee --load-state /var/lib/anvil/state.json --dump-state /var/lib/anvil/state.json --disable-code-size-limit --silent`

`systemd-run --scope --slice=user.slice --unit=alto ./alto run --config "alto-config.json" --port 3000`

After the 1) monitoring is done, 2) is just a matter of computing the final results based on the gathered data. This can be executed in the folder where the measurements were stored with (the outputs will be stored in a *swatts* folder):\

`python3 -m smartwatts \
--input csv --model HWPCReport --files core.csv,msr.csv,rapl.csv --name puller_csv \
--output csv --model PowerReport --directory $(pwd)/swatts/ --name pusher_csv  \
--cpu-base-freq 2200 \
--cpu-tdp 45 \
--cpu-error-threshold 2.0 \
--disable-dram-formula \
--sensor-reports-frequency 500`

**Note** that the setup above might still require fixes for the numerous configuration needed.

### Acknowledgement
This work was supported by a grant from the Romanian Ministry of Research, Innovation and Digitization, CNCS/CCCDI - UEFISCDI, project number 86/2025 ERANET-CHISTERA-IV-SCEAL, within PNCDI IV.

