"""Human labels for the 88-message validation sample.

Each label is the underlying issue read from the customer's own words,
independent of the intake bot's tag (12 of 88 differ from it).
"""
HUMAN_LABELS = {
    # Account & Login (8) - all OTP/login
    "TK-251416": "Account & Login", "TK-243495": "Account & Login", "TK-253164": "Account & Login",
    "TK-244206": "Account & Login", "TK-246118": "Account & Login", "TK-249499": "Account & Login",
    "TK-250628": "Account & Login", "TK-252452": "Account & Login",
    # App & Firmware (7) + one honest relabel (pairing failure is Connectivity)
    "TK-252340": "App & Firmware", "TK-244199": "App & Firmware", "TK-240896": "App & Firmware",
    "TK-254375": "App & Firmware", "TK-254134": "App & Firmware", "TK-250796": "App & Firmware",
    "TK-253691": "App & Firmware", "TK-251431": "Connectivity",
    # Audio Quality (8) - buzzing/distorted/silent/one-direction/mic
    "TK-245896": "Audio Quality", "TK-248313": "Audio Quality", "TK-245322": "Audio Quality",
    "TK-254202": "Audio Quality", "TK-250839": "Audio Quality", "TK-254467": "Audio Quality",
    "TK-253939": "Audio Quality", "TK-247043": "Audio Quality",
    # Billing & Payments (8)
    "TK-243414": "Billing & Payments", "TK-250668": "Billing & Payments", "TK-252127": "Billing & Payments",
    "TK-240500": "Billing & Payments", "TK-249521": "Billing & Payments", "TK-251466": "Billing & Payments",
    "TK-246879": "Billing & Payments", "TK-246628": "Billing & Payments",
    # Charging & Battery (8) - includes the dead-device complaint
    "TK-253604": "Charging & Battery", "TK-251508": "Charging & Battery", "TK-249188": "Charging & Battery",
    "TK-245029": "Charging & Battery", "TK-245237": "Charging & Battery", "TK-244218": "Charging & Battery",
    "TK-246222": "Charging & Battery", "TK-249807": "Charging & Battery",
    # Connectivity (7) + one honest relabel (mic-on-calls is Audio)
    "TK-246317": "Connectivity", "TK-253636": "Connectivity", "TK-252134": "Connectivity",
    "TK-252478": "Connectivity", "TK-240682": "Connectivity", "TK-247675": "Connectivity",
    "TK-241049": "Connectivity", "TK-254098": "Audio Quality",
    # Delivery & Shipping (8) - includes damaged parcel
    "TK-253580": "Delivery & Shipping", "TK-250898": "Delivery & Shipping", "TK-253027": "Delivery & Shipping",
    "TK-250351": "Delivery & Shipping", "TK-243154": "Delivery & Shipping", "TK-242758": "Delivery & Shipping",
    "TK-242476": "Delivery & Shipping", "TK-254137": "Delivery & Shipping",
    # 'Other' bucket honestly relabeled from the messages
    "TK-244818": "Delivery & Shipping",  # change delivery address
    "TK-246719": "Delivery & Shipping",  # cancel before dispatch
    "TK-246396": "Delivery & Shipping",  # address typo, courier can't find
    "TK-248718": "Delivery & Shipping",  # update shipping address
    "TK-241269": "Billing & Payments",   # paid, no order showing
    "TK-253886": "Billing & Payments",   # bank says paid, site says no orders
    "TK-250110": "Billing & Payments",   # paid once, statement disagrees
    "TK-244313": "Charging & Battery",   # battery drains fast
    # Product Enquiry (8) - compatibility questions
    "TK-246082": "Product Enquiry", "TK-243621": "Product Enquiry", "TK-242990": "Product Enquiry",
    "TK-251021": "Product Enquiry", "TK-247719": "Product Enquiry", "TK-243985": "Product Enquiry",
    "TK-254409": "Product Enquiry", "TK-247384": "Product Enquiry",
    # Returns & Refunds (6) + two honest relabels (wrong item in box is Delivery)
    "TK-240920": "Returns & Refunds", "TK-245211": "Returns & Refunds", "TK-249206": "Returns & Refunds",
    "TK-246172": "Returns & Refunds", "TK-245480": "Returns & Refunds", "TK-246955": "Returns & Refunds",
    "TK-252109": "Delivery & Shipping", "TK-251553": "Delivery & Shipping",
    # Warranty & Repair (8) - RMA/service-centre/hardware defects
    "TK-252187": "Warranty & Repair", "TK-253770": "Warranty & Repair", "TK-252058": "Warranty & Repair",
    "TK-253379": "Warranty & Repair", "TK-254700": "Warranty & Repair", "TK-251100": "Warranty & Repair",
    "TK-249419": "Warranty & Repair", "TK-249856": "Warranty & Repair",
}
