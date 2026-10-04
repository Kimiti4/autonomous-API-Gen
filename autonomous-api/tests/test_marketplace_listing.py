import pytest

from app.marketplace.listing import ProductStatus, SoftwareListing


def listing(status=ProductStatus.CERTIFIED):
    return SoftwareListing(
        product_id="product-1",
        version="1.0.0",
        name="Verified App",
        price_minor=1000,
        currency="USD",
        artifact_digest="a" * 64,
        evidence_digest="b" * 64,
        status=status,
        license="standard-commercial",
    )


def test_only_certified_evidence_can_be_listed():
    assert listing().can_list()
    assert listing(ProductStatus.VERIFIED).can_list() is False


def test_publish_changes_certified_product_to_listed():
    assert listing().publish().status is ProductStatus.LISTED


@pytest.mark.parametrize("field,value", (
    ("artifact_digest", "bad"),
    ("evidence_digest", "bad"),
    ("license", ""),
))
def test_invalid_listing_fails_closed(field, value):
    data = listing().__dict__.copy()
    data[field] = value
    with pytest.raises(ValueError, match="marketplace-listing"):
        SoftwareListing(**data).publish()


def test_suspended_product_cannot_publish():
    with pytest.raises(ValueError, match="marketplace-listing"):
        listing(ProductStatus.SUSPENDED).publish()
