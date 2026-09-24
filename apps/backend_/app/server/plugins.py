from litestar_autowire import AutowireConfig, AutowirePlugin

autowire = AutowirePlugin(AutowireConfig(domain_packages=["app.domain"]))
