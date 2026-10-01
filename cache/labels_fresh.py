"""Human labels for the fresh out-of-sample validation draw (seed=123).

Same labeling rules as the tuning sample: the label is the underlying issue in
the customer's own words; 11 of 88 differ from the intake bot's tag.
"""
FRESH_LABELS = {
    # Account & Login (8)
    "TK-240970": "Account & Login", "TK-254485": "Account & Login", "TK-253289": "Account & Login",
    "TK-253210": "Account & Login", "TK-245180": "Account & Login", "TK-250194": "Account & Login",
    "TK-242877": "Account & Login", "TK-241489": "Account & Login",
    # App & Firmware (8)
    "TK-248148": "App & Firmware", "TK-244399": "App & Firmware", "TK-253789": "App & Firmware",
    "TK-253116": "App & Firmware", "TK-243175": "App & Firmware", "TK-254711": "App & Firmware",
    "TK-249613": "App & Firmware", "TK-248020": "App & Firmware",
    # Audio Quality (7) + one relabel (losing the phone at range = Connectivity)
    "TK-243932": "Audio Quality", "TK-250844": "Audio Quality", "TK-249381": "Connectivity",
    "TK-244567": "Audio Quality", "TK-247498": "Audio Quality", "TK-249589": "Audio Quality",
    "TK-248766": "Audio Quality", "TK-246807": "Audio Quality",
    # Billing & Payments (8)
    "TK-240554": "Billing & Payments", "TK-251301": "Billing & Payments", "TK-240503": "Billing & Payments",
    "TK-243658": "Billing & Payments", "TK-253160": "Billing & Payments", "TK-253212": "Billing & Payments",
    "TK-249229": "Billing & Payments", "TK-246916": "Billing & Payments",
    # Charging & Battery (8)
    "TK-244332": "Charging & Battery", "TK-249311": "Charging & Battery", "TK-248387": "Charging & Battery",
    "TK-244267": "Charging & Battery", "TK-250343": "Charging & Battery", "TK-247438": "Charging & Battery",
    "TK-244055": "Charging & Battery",  # device fully unresponsive (dead-device family)
    "TK-240940": "Charging & Battery",
    # Connectivity (8)
    "TK-250427": "Connectivity", "TK-240197": "Connectivity", "TK-244507": "Connectivity",
    "TK-243167": "Connectivity", "TK-245190": "Connectivity", "TK-243199": "Connectivity",
    "TK-250316": "Connectivity", "TK-254263": "Connectivity",
    # Delivery & Shipping (7) + one consistency fix: 'paid on ..., still waiting
    # for something to show up' is the paid-no-order pattern (Billing), matching
    # the label given to the identical message TK-241269 in the tuning draw.
    "TK-252608": "Delivery & Shipping", "TK-245224": "Billing & Payments", "TK-245878": "Delivery & Shipping",
    "TK-248107": "Delivery & Shipping", "TK-246496": "Delivery & Shipping", "TK-240902": "Delivery & Shipping",
    "TK-244667": "Delivery & Shipping", "TK-252529": "Delivery & Shipping",
    # 'Other' bucket relabeled from the messages
    "TK-240887": "Billing & Payments",   # share invoice with GST
    "TK-246637": "Billing & Payments",   # invoice not downloading
    "TK-246312": "Delivery & Shipping",  # package not delivered
    "TK-254390": "Billing & Payments",   # charged twice
    "TK-252699": "Delivery & Shipping",  # cancel before dispatch
    "TK-252884": "Product Enquiry",      # can I connect two cases
    "TK-250436": "Charging & Battery",   # dies by lunchtime
    "TK-250867": "Connectivity",         # pairing light blinks, phone doesn't see it
    # Product Enquiry (8)
    "TK-251936": "Product Enquiry", "TK-244592": "Product Enquiry", "TK-251604": "Product Enquiry",
    "TK-251505": "Product Enquiry", "TK-251965": "Product Enquiry", "TK-244017": "Product Enquiry",
    "TK-246624": "Product Enquiry", "TK-244954": "Product Enquiry",
    # Returns & Refunds (7) + one relabel (outbound courier wait = Delivery)
    "TK-249985": "Returns & Refunds", "TK-244469": "Returns & Refunds", "TK-254065": "Returns & Refunds",
    "TK-243474": "Returns & Refunds", "TK-242843": "Returns & Refunds", "TK-249780": "Delivery & Shipping",
    "TK-245912": "Returns & Refunds", "TK-241463": "Returns & Refunds",
    # Warranty & Repair (7) + one relabel (dead earbud = Audio)
    "TK-251149": "Warranty & Repair", "TK-241844": "Warranty & Repair", "TK-250755": "Warranty & Repair",
    "TK-253219": "Warranty & Repair", "TK-252739": "Warranty & Repair", "TK-248993": "Warranty & Repair",
    "TK-241044": "Warranty & Repair", "TK-246530": "Audio Quality",
}
