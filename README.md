# Yet Another Dex Arb Bot
Explore two and three length arbitrage opportunities on UniswapV2 and UniswapV3 clones.

## How to run
- Replace `.env.example` with `.env`
  ```
  docker run -v $PWD/src:/app/src --name container_name -it image_name
  ```

## TODOs
- Add multicall benchmarks: 10 or single multicall, same contract or different contract etc.
- Add more unit tests, pytest and fixtures
- Fetch the data in `address_data.json`.
- Get rid of two fork dependencies
- `Data` class is weird
- Parametrize v3 fee `[100, 500, 3000, 10000]`
- Fix .env, make publishable image
- Add `__repr__` for key checking and keep `__str__` to log
- Make sure price information is not captured from different blocks
- Handle division errors
- Add a type checking workflow, [for example](https://github.com/BobTheBuidler/dank_mids/blob/master/.github/workflows/mypy.yaml)