import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.domain_loader import load_domain


def test_crafthub_domain_loads() -> None:
    domain = load_domain("crafthub")
    assert domain.manifest.id == "crafthub"
    assert Path(domain.manifest.branding.logo_path).exists()
    assert len(domain.manifest.branding.starter_prompts) == 5
    assert len(domain.manifest.branding.demo_steps) == 4

    cached = [card for card in domain.manifest.branding.starter_prompts if card.eyebrow == "Cached"]
    assert cached and cached[0].prompt == domain.manifest.seed_langcache[0].prompt

    runtime_config = domain.get_runtime_config(settings=None)
    assert runtime_config["memory_similarity_threshold"] == 0.2

    prompt = domain.build_system_prompt(
        mcp_tools=[{"name": "filter_workshop"}, {"name": "filter_storeinventory"}],
        runtime_config={"memory_enabled": True},
    )
    assert "filter_workshop" in prompt
    assert "search_customer_memory" in prompt
    assert "crafthub_order:" in prompt  # the key-prefix warning


def test_crafthub_data_generator_writes_expected_files(tmp_path: Path) -> None:
    domain = load_domain("crafthub")
    result = domain.generate_demo_data(output_dir=tmp_path, update_env_file=False)
    assert result.env_updates["DEMO_USER_ID"] == domain.manifest.identity.default_id
    assert result.env_updates["DEMO_USER_HOME_STORE_ID"] == "STORE_001"
    assert result.summary["products"] >= 20
    for spec in domain.get_entity_specs():
        assert (tmp_path / spec.file_name).exists()

    workshops = [
        json.loads(line)
        for line in (tmp_path / "workshops.jsonl").read_text().splitlines()
        if line.strip()
    ]
    now = datetime.now(timezone.utc)
    assert all(datetime.fromisoformat(row["start_time"]) > now for row in workshops)
    assert any(row["store_id"] == "STORE_001" and row["seats_available"] == 0 for row in workshops)


def test_crafthub_data_generator_applies_transform(tmp_path: Path) -> None:
    domain = load_domain("crafthub")
    module = __import__("domains.crafthub.data_generator", fromlist=["generate_demo_data"])

    def rename(value):
        if isinstance(value, str):
            return value.replace("CraftHub", "Acme Crafts")
        if isinstance(value, list):
            return [rename(item) for item in value]
        if isinstance(value, dict):
            return {key: rename(item) for key, item in value.items()}
        return value

    result = module.generate_demo_data(output_dir=tmp_path, transform=rename)
    assert result.env_updates["DEMO_USER_HOME_STORE_NAME"] == "Acme Crafts Las Colinas"
    for spec in domain.get_entity_specs():
        text = (tmp_path / spec.file_name).read_text()
        assert "CraftHub" not in text
