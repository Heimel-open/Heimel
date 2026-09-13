# Bazoom DOM runtime

Status: active delivery

Base: e228dc567884f5d4f4327e4d16e6911ae6055c10

Adds a browser/DOM boundary that:
- captures visible Bazoom page state into BazoomPageSnapshot
- applies precomputed article/review writes to mapped DOM fields
- keeps credentials outside Function Fabric
- keeps submission behind an explicit human gate
- fails closed when a write field has no configured selector

This layer does not generate content, bypass task restrictions, or auto-submit.
