#pragma once
#include <gio/gio.h>
#include "cix_stream.h"
G_BEGIN_DECLS
#define CIX_TYPE_GCONVERTER (cix_gconverter_get_type())
G_DECLARE_FINAL_TYPE(CixGConverter, cix_gconverter, CIX, GCONVERTER, GObject)
CixGConverter *cix_gconverter_new(gboolean encoder, const cix_options_v1 *options, GError **error);
/* Thread-safe entry fence; an in-flight native codec call is not preempted.
 * Keep the object alive while cancelling. reset clears cancellation. */
void cix_gconverter_cancel(CixGConverter *converter);
G_END_DECLS
