#!/usr/bin/env python3
"""Validate EVENTS.yaml structure: required keys, event/trigger fields."""

import sys

import yaml

data = yaml.safe_load(open("EVENTS.yaml"))
errors = []

if not data:
    errors.append("EVENTS.yaml is empty")
else:
    for key in ["standard_funnel", "custom_events"]:
        if key not in data:
            errors.append(f'missing required key "{key}"')
    for section in ["standard_funnel", "payment_funnel"]:
        if section in data and data[section]:
            for i, ev in enumerate(data[section]):
                if "event" not in ev:
                    errors.append(f'{section}[{i}] missing "event"')
                if "trigger" not in ev:
                    errors.append(f'{section}[{i}] missing "trigger"')

if errors:
    print("EVENTS.yaml issues:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
