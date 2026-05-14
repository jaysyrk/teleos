package io.teleos;

import java.lang.annotation.*;

/**
 * Marks a class method or type as providing a Teleos fact.
 *
 * <pre>
 * {@literal @}TeleosFact("alice is admin")
 * {@literal @}TeleosFact("document is confidential")
 * {@literal @}TeleosRule("if X is admin then X can access Y")
 * public class AccessPolicy {}
 *
 * Engine engine = Engine.from(AccessPolicy.class);
 * engine.ask("alice can access document");  // true
 * </pre>
 */
@Repeatable(TeleosFacts.class)
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface TeleosFact {
    String value();
}
