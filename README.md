# Lore marketplace

The public list of Lore sellers. One file, `marketplace.json`, one entry per seller, each pointing at a node an agent can query and buy from.

Agents read the file straight from this repo:

```
https://raw.githubusercontent.com/dipakkrishnan/lore-marketplace/main/marketplace.json
```

## What an entry is

Only what a seller's store already shows anyone who visits it: a display name, the node's `/mcp` endpoint, the store page, the network payments settle on, the topics on offer, how many publications there are, and the prices. No private memory, no payout addresses, no identity the seller did not choose. `schema.json` pins the shape.

## How an agent uses it

1. Fetch `marketplace.json` and pick sellers whose `topics` match the task.
2. Call `discover` on each chosen `node`. It is free and returns every publication's teaser and id.
3. Call `get` with an id to buy one publication. The node answers with an x402 challenge, priced at `price_usd`, and settles in USDC on `network`. Nodes that offer answers from the owner's proxy list `answer_price_usd`.

A seller's node is theirs. This file only says where it is.

## How to list

From the Lore app, choose **List on the marketplace** in Settings. It sends your entry as a pull request here; you are pending until it is merged, then listed.

By hand, add an entry to `sellers` in `marketplace.json` and open a pull request. The check runs `scripts/validate.py --live`, which validates the file and asks your store to answer. To delist, open a pull request that removes your entry.

## Rules

- Listing is opt-in. Nothing is added on a seller's behalf.
- An entry must match what the node's `discover` returns. Drift gets fixed or removed.
- A store that stops answering is removed.
