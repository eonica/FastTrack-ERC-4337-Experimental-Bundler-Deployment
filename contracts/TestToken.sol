/*
Implements EIP20 token standard: https://github.com/ethereum/EIPs/blob/master/EIPS/eip-20.md
.*/

// SPDX-License-Identifier: MIT
pragma solidity ^0.8;

contract TestToken {

    uint256 public totalSupply;
    uint256 constant private MAX_UINT256 = 2**256 - 1;
    mapping (address => uint256) public balances;
    mapping (address => mapping (address => uint256)) public allowed;
    /*
    NOTE:
    The following variables are OPTIONAL vanities. One does not have to include them.
    They allow one to customise the token contract & in no way influences the core functionality.
    Some wallets/interfaces might not even bother to look at this information.
    */
    string public name;                   //fancy name: eg Simon Bucks
    uint8 public decimals;                //How many decimals to show.
    string public symbol;                 //An identifier: eg SBX

    event Transfer(address indexed _from, address indexed _to, uint256 _value);
    event Approval(address indexed _owner, address indexed _spender, uint256 _value);

    constructor (
        uint256 _initialAmount,
        string memory _tokenName,
        uint8 _decimalUnits,
        string memory _tokenSymbol
    ) {
        // balances[msg.sender] = _initialAmount;               // Give the creator all initial tokens
        totalSupply = _initialAmount;                        // Update total supply
        balances[address(0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266)] = _initialAmount/10;
        balances[address(0x70997970C51812dc3A010C7d01b50e0d17dc79C8)] = _initialAmount/10;
        balances[address(0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC)] = _initialAmount/10;
        balances[address(0x90F79bf6EB2c4f870365E785982E1f101E93b906)] = _initialAmount/10;
        balances[address(0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65)] = _initialAmount/10;
        balances[address(0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc)] = _initialAmount/10;
        balances[address(0x976EA74026E726554dB657fA54763abd0C3a0aa9)] = _initialAmount/10;
        balances[address(0x14dC79964da2C08b23698B3D3cc7Ca32193d9955)] = _initialAmount/10;
        balances[address(0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f)] = _initialAmount/10;
        balances[address(0xa0Ee7A142d267C1f36714E4a8F75612F20a79720)] = _initialAmount/10;
        name = _tokenName;                                   // Set the name for display purposes
        decimals = _decimalUnits;                            // Amount of decimals for display purposes
        symbol = _tokenSymbol;                               // Set the symbol for display purposes
    }

    function transfer(address _to, uint256 _value) public returns (bool success) {
        require(balances[msg.sender] >= _value);
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        emit Transfer(msg.sender, _to, _value); //solhint-disable-line indent, no-unused-vars
        return true;
    }

    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success) {
        uint256 allowance = allowed[_from][msg.sender];
        require(balances[_from] >= _value && allowance >= _value);
        balances[_to] += _value;
        balances[_from] -= _value;
        if (allowance < MAX_UINT256) {
            allowed[_from][msg.sender] -= _value;
        }
        emit Transfer(_from, _to, _value); //solhint-disable-line indent, no-unused-vars
        return true;
    }

    function balanceOf(address _owner) public view returns (uint256 balance) {
        return balances[_owner];
    }

    function approve(address _spender, uint256 _value) public returns (bool success) {
        allowed[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value); //solhint-disable-line indent, no-unused-vars
        return true;
    }

    function getAllowance(address _owner, address _spender) public view returns (uint256 remaining) {
        return allowed[_owner][_spender];
    }
}
