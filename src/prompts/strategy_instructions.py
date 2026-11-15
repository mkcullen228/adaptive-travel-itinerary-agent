
MINIMAL_DISRUPTION_INSTRUCTION = """
Prioritize preserving the original itinerary.

Minimize changes to existing activities, scheduled
times, durations, and sequence wherever feasible.

Modify or remove activities only when required by
confirmed disruptions or schedule feasibility.

Avoid unnecessary replacement activities. Do not
proactively fill open time slots simply to maintain
a full itinerary.

Preserve mandatory constraints and explain any
trade-offs involving flexible preferences.

Do not sacrifice feasibility simply to minimize changes.
"""


BEST_OVERALL_FEASIBILITY_INSTRUCTION = """
Prioritize producing the most feasible recovery
proposal supported by available evidence.

Preserve all mandatory constraints.

Make reasonable changes to flexible activities,
including removing multiple optional activities
when necessary to improve feasibility.

Consider replacement activities when they improve
schedule feasibility and availability is sufficiently
supported by evidence.

Prioritize reliable venue information, realistic
walking estimates, and schedule feasibility.

Explain removals, replacements, trade-offs, and
remaining uncertainties.

Do not claim feasibility before deterministic validation.
"""


PREFERENCE_ORIENTED_INSTRUCTION = """
Prioritize preserving the user's high-priority
flexible preferences.

Favor activities and replacements that align with
the user's stated interests and preferences.

When appropriate, replace existing optional activities
with better preference-aligned alternatives, even
if this requires more changes to the original itinerary.

Consider preference priority when trade-offs are
necessary, without treating flexible preferences
as mandatory constraints.

Only propose replacements supported by sufficient
availability evidence.

Explain compromises, trade-offs, and remaining
uncertainties.

Do not sacrifice schedule feasibility or mandatory
constraints to satisfy preferences.
"""
