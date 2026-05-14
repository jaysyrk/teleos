package io.teleos;

import java.lang.annotation.*;

/** Container for repeated {@link TeleosRule} annotations. */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface TeleosRules {
    TeleosRule[] value();
}
