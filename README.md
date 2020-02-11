[Installation](#installation) |
[Getting Started](#getting-started) |
[Contributing](#contributing) |
[Acknowledgements](#acknowledgements)

# Knowledge Graph Forge

A domain-agnostic, generic and extensible Python framework for **consistently**
building and interacting with knowledge graphs in a data science context.

This framework builds a **bridge** between data engineers, knowledge engineers,
and data scientists in the context of knowledge graphs by making easier for:

- **data engineers** to define, execute, and share data transformations in a traceable way,
- **knowledge engineers** to define and share knowledge representations of heterogeneous data,
- **data scientists** to query and register data during their analysis without
having to worry about the semantic formats and technologies,

while guaranteeing the consistency of operations with a **knowledge graph
schema** like [Neuroshapes](https://github.com/INCF/neuroshapes).

The architectural design choices:
 1) be generic on where it brings **flexibility** for adaptation to multiple ecosystems,
 2) be opinionated on where it simplifies the complexity,
 3) have strong separation of concern with delegation to the lowest level for **modularity**.

## Installation

Stable version

```bash
pip install kgforge
```

Upgrade to latest version

```bash
pip install --upgrade kgforge
```

Development version

```bash
pip install git+https://github.com/BlueBrain/kgforge
```

## Getting Started

See in the directory `examples` for examples of usages, configurations, mappings.

### User API

Forge 

```bash
KnowledgeGraphForge(configuration: Union[str, Dict], **kwargs)
```

Resources

```bash
Resource(**properties)

Dataset(forge: KnowledgeGraphForge, type: str = "Dataset", **properties)
  add_parts(resources: List[Resource], versioned: bool = True) -> None
  add_distribution(path: str) -> None
  add_contribution(agent: str, **kwargs) -> None
  add_generation(**kwargs) -> None
  add_derivation(resource: Resource, versioned: bool = True, **kwargs) -> None
  add_invalidation(**kwargs) -> None
  add_files(path: str) -> None
  download(source: str, path: str) -> None
```

Modeling

```bash
prefixes() -> Dict[str, str]
types() -> List[str]
template(type: str, only_required: bool = False) -> None
validate(data: Union[Resource, List[Resource]]) -> None
```

Resolving

```bash
resolve(text: str, scope: Optional[str] = None, resolver: Optional[str] = None, target: Optional[str] = None, type: Optional[str] = None, strategy: ResolvingStrategy = ResolvingStrategy.BEST_MATCH) -> Optional[Union[Resource, List[Resource]]]
```

Formatting

```bash
format(what: str, *args) -> str
```

Mapping

```bash
mappings(source: str) -> Dict[str, List[str]]
mapping(type: str, source: str, mapping_type: Callable = DictionaryMapping) -> Mapping
map(data: Any, mapping: Union[Mapping, List[Mapping]], mapper: Callable, na: Union[Any, List[Any]] = None) -> Union[Resource, List[Resource]]
```

Reshaping

```bash
reshape(data: Union[Resource, List[Resource]], keep: List[str], versioned: bool = False) -> Union[Resource, List[Resource]]
```

Querying

```bash
retrieve(id: str, version: Optional[Union[int, str]] = None) -> Resource:
paths(type: str) -> PathsWrapper:
search(*filters, **params) -> List[Resource]
sparql(query: str) -> List[Resource]
download(data: Union[Resource, List[Resource]], follow: str, path: str) -> None
```

Storing

```bash
register(data: Union[Resource, List[Resource]]) -> None
update(data: Union[Resource, List[Resource]]) -> None
deprecate(data: Union[Resource, List[Resource]]) -> None
```

Versioning

```bash
tag(data: Union[Resource, List[Resource]], value: str) -> None
freeze(data: Union[Resource, List[Resource]]) -> None
```

Files handling

```bash
attach(path: str) -> LazyAction
```

Converting

```bash
as_json(data: Union[Resource, List[Resource]], expanded: bool = False, store_metadata: bool = False) -> Union[Dict, List[Dict]]
as_jsonld(data: Union[Resource, List[Resource]], compacted: bool = True, store_metadata: bool = False) -> Union[Dict, List[Dict]]
as_triples(data: Union[Resource, List[Resource]], store_metadata: bool = False) -> List[Tuple[str, str, str]]
as_dataframe(data: List[Resource], na: Union[Any, List[Any]] = [None], nesting: str = ".", expanded: bool = False, store_metadata: bool = False) -> DataFrame
from_json(data: Union[Dict, List[Dict]], na: Union[Any, List[Any]] = None) -> Union[Resource, List[Resource]]
from_jsonld(data: Union[Dict, List[Dict]]) -> Union[Resource, List[Resource]]
from_triples(data: List[Tuple[str, str, str]]) -> Union[Resource, List[Resource]]
from_dataframe(data: DataFrame, na: Union[Any, List[Any]] = np.nan, nesting: str = ".") -> Union[Resource, List[Resource]]
```

### Internals

**Archetypes**

Mapper

```bash
Mapper(forge: Optional["KnowledgeGraphForge"] = None)
  map(data: Any, mapping: Union[Mapping, List[Mapping]], na: Union[Any, List[Any]]) -> Union[Resource, List[Resource]]
```

Mapping

```bash
Mapping(mapping: str)
  load(source: str) -> Mapping
  save(path: str) -> None
```

Model

```bash
Model(source: str, **source_config)
  prefixes() -> Dict[str, str]
  types() -> List[str]
  template(type: str, only_required: bool) -> str
  mappings(data_source: str) -> Dict[str, List[str]]
  mapping(type: str, data_source: str, mapping_type: Callable) -> Mapping
  validate(data: Union[Resource, List[Resource]]) -> None
```

Resolver

```bash
Resolver(source: str, targets: List[Dict[str, str]], result_resource_mapping: str, **source_config)
  resolve(text: str, target: Optional[str], type: Optional[str], strategy: ResolvingStrategy) -> Optional[Union[Resource, List[Resource]]]
```

Store

```bash
Store(endpoint: Optional[str] = None, bucket: Optional[str] = None, token: Optional[str] = None, versioned_id_template: Optional[str] = None, file_resource_mapping: Optional[str] = None))
  register(data: Union[Resource, List[Resource]]) -> None
  upload(path: str) -> Union[Resource, List[Resource]]
  retrieve(id: str, version: Optional[Union[int, str]]) -> Resource
  download(data: Union[Resource, List[Resource]], follow: str, path: str) -> None
  update(data: Union[Resource, List[Resource]]) -> None
  tag(data: Union[Resource, List[Resource]], value: str) -> None
  deprecate(data: Union[Resource, List[Resource]]) -> None
  search(resolvers: List[Resolver], *filters, **params) -> List[Resource]
  sparql(prefixes: Dict[str, str], query: str) -> List[Resource]
  freeze(data: Union[Resource, List[Resource]]) -> None
```

**Archetype specializations**

Mappers

```bash
DictionaryMapper
[TODO] R2RmlMapper
[TODO] ResourceMapper
[TODO] TableMapper
```

Mappings

```bash
DictionaryMapping
```

Models

```bash
DemoModel
[Work In Progress] Neuroshapes
```

Resolvers

```bash
DemoResolver
```

Stores

```bash
DemoStore
[TODO] RdfLibGraph
[Work In Progress] BlueBrainNexus
```

## Contributing

Please add `@pafonta` as reviewer if your Pull Request modifies `core`.

Setup

```bash
git clone https://github.com/BlueBrain/kgforge
pip install --editable kgforge[dev]
```

Checks before committing

```bash
tox
```

### Styling

[PEP 8](https://www.python.org/dev/peps/pep-0008/),
[PEP 257](https://www.python.org/dev/peps/pep-0257/), and
[PEP 20](https://www.python.org/dev/peps/pep-0020/) must be followed.

### Releasing

```bash
# Setup
pip install --upgrade pip setuptools wheel twine

# Checkout
git checkout master
git pull upstream master

# Check
tox

# Tag
git tag -a v<x>.<y>.<z> HEAD
git push upstream v<x>.<y>.<z>

# Build
python setup.py sdist bdist_wheel

# Upload
twine upload dist/*

# Clean
rm -R build dist *.egg-info
```

## Acknowledgements

This project has received funding from the EPFL Blue Brain Project (funded by
the Swiss government’s ETH Board of the Swiss Federal Institutes of Technology)
and from the European Union’s Horizon 2020 Framework Programme for Research and
Innovation under the Specific Grant Agreement No. 785907 (Human Brain Project SGA2).
