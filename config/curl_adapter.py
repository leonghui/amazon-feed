from curl_adapter.curl_cffi import CurlCffiAdapter


curl_cffi_adapter: CurlCffiAdapter = CurlCffiAdapter(
    # This is the default
    impersonate_browser_type="chrome",
    # Optionally set additional options
#     tls_configuration_options={
#         "ja3_str": "...",
#         "akamai_str": "...",
#         "extra_fp": ExtraFingerprints(...),
#     },
)
