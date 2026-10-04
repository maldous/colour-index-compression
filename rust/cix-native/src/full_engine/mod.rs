//! Native specialist ports under qualification.
//!
//! These modules expose exact transforms and explicit backend interfaces. They
//! are not admitted to CLI selection until their reference parity, resource
//! contracts and archive-only restoration have been qualified.
pub mod address_relations;
pub mod arithmetic;
pub mod backend_provider;
pub mod bounded_values;
pub mod catalogue;
pub mod conditional_values;
pub mod containers;
pub mod dispatch;
pub mod graph_residuals;
pub mod jxl_provider;
pub mod mixed;
pub mod record_ordering;
pub mod regions;
pub mod strided_values;
pub mod structured_frames;
pub mod volume_lifting;
