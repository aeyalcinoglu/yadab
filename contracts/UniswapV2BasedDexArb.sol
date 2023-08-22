// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.6.6;

import "./uniswap/interfaces/IERC20.sol";
import "./uniswap/interfaces/IUniswapV2Factory.sol";
import "./uniswap/interfaces/IUniswapV2Router02.sol";
import "./uniswap/interfaces/IUniswapV2Pair.sol";

contract UniswapV2BasedDexArb {
  address public owner;
  
  constructor() {
    owner = msg.sender;
  }
  
  event Profit(address indexed _from, int indexed profit, uint _value);
  event CallbackSender(address indexed _from, address indexed _sender, uint _value);

  function check(address _tokenPay, address _tokenSwap, uint _amountTokenPay, address _sourceRouter, address _targetRouter) public view returns (int, uint) {
    address[] memory path1 = new address[](2);
    address[] memory path2 = new address[](2);
    path1[0] = path2[1] = _tokenPay;
    path1[1] = path2[0] = _tokenSwap;

    uint amountOut = IUniswapV2Router02(_sourceRouter).getAmountsOut(_amountTokenPay, path1)[1];
    uint amountRepay = IUniswapV2Router02(_targetRouter).getAmountsOut(amountOut, path2)[1];
    int profit = 0;
    unchecked {
      profit = int(amountRepay - _amountTokenPay);
    }

    return (
        profit,
        amountOut
    );
  }
  function startArbitrage (
    address _tokenPay,
    address _tokenSwap,
    uint _amountTokenPay,
    address _sourceRouter,
    address _targetRouter,
    address _sourceFactory
  ) external payable {
      (int profit, uint _tokenBorrowAmount) = check(_tokenPay, _tokenSwap, _amountTokenPay, _sourceRouter, _targetRouter);

      emit Profit(msg.sender, profit, msg.value);

      address pairAddress = IUniswapV2Factory(_sourceFactory).getPair(_tokenPay, _tokenSwap);
      require(pairAddress != address(0), 'e10');
      address token0 = IUniswapV2Pair(pairAddress).token0();
      address token1 = IUniswapV2Pair(pairAddress).token1();
      require(token0 != address(0) && token1 != address(0), 'e11');

      IUniswapV2Pair(pairAddress).swap(
          _tokenSwap == token0 ? _tokenBorrowAmount : 0,
          _tokenSwap == token1 ? _tokenBorrowAmount : 0,
          address(this),
          abi.encode(_sourceRouter, _targetRouter)
      );
  }


  function execute(
    address _sender,
    uint _amount0,
    uint _amount1,
    bytes calldata _data
) internal {
    emit CallbackSender(msg.sender, _sender, msg.value);

    uint amountToken = _amount0 == 0 ? _amount1 : _amount0;

    IUniswapV2Pair iUniswapV2Pair = IUniswapV2Pair(msg.sender);
    address token0 = iUniswapV2Pair.token0();
    address token1 = iUniswapV2Pair.token1();

    address[] memory path1 = new address[](2);
    address[] memory path2 = new address[](2);

    address forward = _amount0 == 0 ? token1 : token0;
    address backward = _amount0 == 0 ? token0 : token1;

    path1[0] = path2[1] = forward;
    path1[1] = path2[0] = backward;

    (address sourceRouter, address targetRouter) = abi.decode(_data, (address, address));
    require(sourceRouter != address(0) && targetRouter != address(0), 'e12');

    IERC20 token = IERC20(forward);
    token.approve(targetRouter, amountToken);

    uint amountRequired = IUniswapV2Router02(sourceRouter).getAmountsIn(amountToken, path2)[0];
    uint amountReceived = IUniswapV2Router02(targetRouter).swapExactTokensForTokens(
        amountToken,
        0,
        path1,
        address(this), 
        block.timestamp + 60
    )[1];

    IERC20 otherToken = IERC20(backward);

    otherToken.transfer(msg.sender, amountRequired);
    otherToken.transfer(owner, amountReceived - amountRequired);
    require(amountReceived > amountRequired, 'flashloan failed');

  }

    function pancakeCall(address _sender, uint256 _amount0, uint256 _amount1, bytes calldata _data) external {
      execute(_sender, _amount0, _amount1, _data);
    }
    function waultSwapCall(address _sender, uint256 _amount0, uint256 _amount1, bytes calldata _data) external {
      execute(_sender, _amount0, _amount1, _data);
    }

    function uniswapV2Call(address _sender, uint256 _amount0, uint256 _amount1, bytes calldata _data) external {
        execute(_sender, _amount0, _amount1, _data);
    }
}
