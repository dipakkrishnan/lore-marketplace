# Lore marketplace

The public list of Lore sellers. One file, `marketplace.json`, one entry per seller, each pointing at a node an agent can query and buy from.

Agents read the file straight from this repo:

```
https://raw.githubusercontent.com/dipakkrishnan/lore-marketplace/main/marketplace.json
```

## What an entry is

Only what a seller's store already shows anyone who visits it: a display name, the node's `/mcp` endpoint, the store page, the network payments settle on, the topics on offer, how many publications there are, any collections with their size, and the prices. No private memory, no payout addresses, no identity the seller did not choose. `schema.json` pins the shape.

## How an agent uses it

1. Fetch `marketplace.json` and pick sellers whose `topics` match the task.
2. Call `discover` on each chosen `node`. It is free and returns every publication's teaser and id.
3. Call `get` with an id to buy one publication. The node answers with an x402 challenge, priced at `price_usd`, and settles in USDC on `network`. Nodes that offer answers from the owner's proxy list `answer_price_usd`.
4. A seller may also sell `collections`: sets of pieces bought together in one call at `price_usd`. `discover` names each one's tool and pieces.

A seller's node is theirs. This file only says where it is.

## How to list

From the Lore app, choose **List** in Settings. It switches your store on for the marketplace, so its `discover` says `"listed": true` and the name you chose, then opens the **List my store** issue form here with your address filled in. Submit it and the `refresh` workflow reads your store, adds it, and replies on the issue.

To delist, choose **Delist** in the app. Your store then says `"listed": false` and leaves the list at the next daily refresh.

## How it stays current

The node is the source of truth. Every day `.github/workflows/refresh.yml` calls `discover` on every node and rewrites each entry from what it says. A node that asks not to be listed is dropped at once; one that stops answering, or stops qualifying, is marked `down_since` and dropped after seven days.

## Rules

- Listing is opt-in, and only the node can opt in: an entry needs `"listed": true` from the node's own `discover`, so owning the node is what counts.
- A node needs real payments (Base mainnet) and at least one publication.
- Changes by pull request are checked with `scripts/validate.py --live`, which calls `discover` on the entries the pull request changes.
