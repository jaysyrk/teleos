package io.teleos;

import java.lang.annotation.*;

/** Marks a class as providing a Teleos rule. Repeatable. */
@Repeatable(TeleosRules.class)
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface TeleosRule {
    String value();
}
