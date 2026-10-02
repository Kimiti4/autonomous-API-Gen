from app.engine.schema_ir import SchemaField, SchemaIR, compare_schemas, validate_schema


def test_schema_ir_validates_structural_contract():
    schema = SchemaIR("WalletView", fields=(
        SchemaField("wallet_id", "string", format="uuid"),
        SchemaField("balance", "number"),
        SchemaField("currency", "string"),
    ))
    assert validate_schema(schema) == ()


def test_schema_comparison_detects_requiredness_and_type_drift():
    expected = SchemaIR("WalletView", fields=(
        SchemaField("wallet_id", "string", format="uuid"),
        SchemaField("balance", "number"),
    ))
    actual = SchemaIR("WalletView", fields=(
        SchemaField("wallet_id", "integer", required=False),
        SchemaField("balance", "string"),
    ))
    findings = compare_schemas(expected, actual)
    assert any("type mismatch" in x for x in findings)
    assert any("requiredness" in x for x in findings)


def test_schema_rejects_arrays_without_item_type():
    schema = SchemaIR("WalletList", fields=(SchemaField("items", "array"),))
    assert any("array item type" in x for x in validate_schema(schema))
