# Install experience fixtures

`tests/e2e/run_e2e.py` builds the current checkout wheel, resolves its dependency
wheels once, records `manifest.json`, and uses that temporary wheelhouse for all
isolated local/global cases. Product runtimes never import from the checkout.
