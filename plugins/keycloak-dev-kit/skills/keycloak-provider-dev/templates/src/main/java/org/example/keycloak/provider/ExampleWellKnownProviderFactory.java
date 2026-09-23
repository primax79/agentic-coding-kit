package org.example.keycloak.provider;

import java.util.Map;

import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.wellknown.WellKnownProvider;
import org.keycloak.wellknown.WellKnownProviderFactory;

/**
 * Minimal example provider: serves {@code /realms/{realm}/.well-known/example-provider}.
 * Registered in {@code META-INF/services/org.keycloak.wellknown.WellKnownProviderFactory}.
 * A {@code String} result is served as {@code application/jwt}, anything else as JSON.
 */
public class ExampleWellKnownProviderFactory implements WellKnownProviderFactory {

    public static final String PROVIDER_ID = "example-provider";

    @Override
    public WellKnownProvider create(KeycloakSession session) {
        return new WellKnownProvider() {
            @Override
            public Object getConfig() {
                return Map.of("realm", session.getContext().getRealm().getName());
            }

            @Override
            public void close() {
            }
        };
    }

    @Override
    public void init(Config.Scope config) {
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
    }

    @Override
    public void close() {
    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }
}
