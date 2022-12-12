# MSWetterbericht

A tool for the creation of a "Financial Weather Forecast" created for the
[Mauerstrassenwetten](https://reddit.com/r/mauerstrassenwetten) subreddit.
The tool is used to post the weather forecast to the Daily Thread of this subreddit.

The tool consists of two parts:

- `wetterbericht.py`: The main part. A modularised Python script which scrapes several websites for financial
  instrument data. It's easily extendable with new methods or instruments (see below)
- `pfostierer.py`: A makeshift script to find the correct thread on the subreddit and post the result of
  the `wetterbericht.py` script

# Installation

The **MSWetterbericht** can be initialised via [Poetry](https://python-poetry.org/) by running
`poetry install` in the source directory after cloning the repository.

# Extending the Wetterbericht

## Adding new properties or prefixes

The properties (like "explodiert") and prefixes (like "geringfügig") for the forecast are located in the
[`prose.yaml` file](https://github.com/m3adow/mswetterbericht/blob/main/files/prose.yaml). Simply add a new list item
to the instrument type you find fitting.

## Adding more instruments

The MSWetterbericht works via submodules for websites which are called data providers. There are either "full-fledged"
data providers which should work for all or at least some instruments provided by the website they are used for and
there are "half-assed" data providers which have only been written with one or two instruments in mind and will very
likely not work for any other instrument.

There are currently (_Dec-2022_) three full-fledged
[data providers](https://github.com/m3adow/mswetterbericht/tree/main/mswetterbericht/data_providers) for
[CNBC](https://www.cnbc.com/world/), [Yahoo Finance](https://finance.yahoo.com/) and
[Investing.com](https://www.investing.com/) as well as one half-assed data provider for
[onvista.de](https://www.onvista.de/).

There are two ways to extend the Wetterberichts instruments. Either by using an existing data provider to add a new
instrument or by adding a new data provider for a new instrument.

### Adding a new instrument to an existing data provider

Adding a new instrument to an existing data provider can easily be achieved by adding a new list entry to the
[`instruments.yaml` file](https://github.com/m3adow/mswetterbericht/blob/main/files/instruments.yaml).

An instrument entry consists of:

| **Key**       | **Description**                                                                                             | **Example**                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `description` | Name and/or description of the instument                                                                    | 💦🦡 Zukünfte                                   |
| `symbol`      | The symbol used to identify the instrument with the data provider                                           | NQ=F                                            |
| `url`         | The URL to the symbols overview at the data providers web site                                              | https://finance.yahoo.com/quote/NQ%3DF?p=NQ%3DF |
| `plural`      | A `bool` which signals if the instrument is used as plural or singular (e.g. "Futures" is plural)           | true                                            |
| `priority`    | The priority the instrument has, the higher the priority, the earlier it will be added to the forecast list | 50                                              |
| `type`        | The type of the instrument which is used for it's prose line and its prose properties and prefixes          | boring                                          |

In YAML this would result in:

```yaml
- description: 💦🦡 Zukünfte
  symbol: NQ=F
  url: https://finance.yahoo.com/quote/NQ%3DF?p=NQ%3DF
  # The following attributes can be omitted due to being defaults
  plural: true
  priority: 50
  type: boring
```

To keep repetition at a minimum, there are `defaults` defined at the top of the `instruments.yaml` file which will be
used if an instrument is missing that key, as pointed out by the comment above.

### Adding a new instrument to an existing data provider

_Soon™_
