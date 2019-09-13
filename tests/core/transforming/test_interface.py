from kgforge.core.transforming.mapping import Mapper


class TestResources:

    def test_map_from(self, tmp_path, mocker, forge, mapper):
        mocker.patch("kgforge.core.mapping.Mapper.apply")
        forge.resources.map_from(tmp_path, mapper)
        Mapper.apply.assert_called_once()