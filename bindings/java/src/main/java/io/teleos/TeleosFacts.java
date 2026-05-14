package io.teleos;

import java.lang.annotation.*;

/** Container for repeated {@link TeleosFact} annotations. */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface TeleosFacts {
    TeleosFact[] value();
}
