/**
# dye Injection for Flow Visualization

This module introduces a circular tracer (dye) into the flow at a specified time 
and location. The dye then advects with the flow, allowing visualization of flow 
patterns. This is useful for visualizing complex flow structures in simulations
like lid-driven cavity flow.

## Parameters
- `tInjection`: time at which to inject the dye
- `xInjection`, `yInjection`: position where the dye is injected
- `dyeRadius`: radius of the circular dye
*/

#include "tracer.h"

// dye tracer parameters (can be overridden by the user)
double tInjection = 0.1;  // Default injection time
double xInjection = 0.0;  // Default X-position for injection
double yInjection = 0.0;  // Default Y-position for injection
double dyeRadius = 0.05;  // Default radius of the circular dye

// Define the scalar field for the dye
scalar T[];
scalar * tracers = {T};

// Initialize the dye tracer to zero everywhere
event init (t = 0) {
  foreach()
    T[] = 0.0;
}

// Inject the dye at the specified time
event inject_dye (t = tInjection) {
  fprintf(stderr, "Injecting dye at t = %g, position = (%g, %g), radius = %g\n", 
          t, xInjection, yInjection, dyeRadius);
  
  // Set dye concentration to 1.0 within the circular region
  foreach() {
    double dist = sqrt(sq(x - xInjection) + sq(y - yInjection));
    if (dist <= dyeRadius)
      T[] = 1.0;
  }
}