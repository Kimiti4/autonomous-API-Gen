import pytest
from app.marketplace.listing import HumanMarketplaceAuthorization, ProductStatus, SoftwareListing, authorization_digest

def listing(status=ProductStatus.CERTIFIED):
    return SoftwareListing("product-1","1.0.0","Verified App",1000,"USD","a"*64,"b"*64,status,"standard-commercial")

def auth(action="list", product_id="product-1"):
    return HumanMarketplaceAuthorization(f"auth-{action}","human-operator",action,product_id,"b"*64)

def test_listing_requires_explicit_human_authorization():
    with pytest.raises(ValueError,match="human-authorization"): listing().publish()
    assert listing().publish(auth()).status is ProductStatus.LISTED

def test_sale_requires_separate_human_authorization():
    listed=listing().publish(auth())
    with pytest.raises(ValueError,match="human-authorization"): listed.sell()
    assert listed.sell(auth("sell")).status is ProductStatus.SOLD

def test_authorization_is_bound_to_product_and_evidence():
    assert not auth().permits("list","other-product","b"*64)
    assert not auth().permits("list","product-1","c"*64)
    assert len(authorization_digest(auth()))==64

@pytest.mark.parametrize("field,value",(("artifact_digest","bad"),("evidence_digest","bad"),("license","")))
def test_invalid_listing_fails_closed(field,value):
    data=listing().__dict__.copy(); data[field]=value
    with pytest.raises(ValueError,match="marketplace"): SoftwareListing(**data).publish(auth())

def test_non_certified_product_cannot_publish():
    with pytest.raises(ValueError,match="marketplace"): listing(ProductStatus.VERIFIED).publish(auth())

def test_suspended_product_cannot_publish():
    with pytest.raises(ValueError,match="marketplace"): listing(ProductStatus.SUSPENDED).publish(auth())
