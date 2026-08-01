/*
 * Copyright 2026 Jetperch LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <setjmp.h>
#include <cmocka.h>
#include "jsdrv_prv/msg_queue.h"
#include "jsdrv_prv/frontend.h"
#include "jsdrv_prv/list.h"
#include "jsdrv_prv/platform.h"
#include "jsdrv/cstr.h"

#if _WIN32
#include <windows.h>
#else
#include <poll.h>
#endif


// linker stubs: jsdrv_support_objlib's pubsub.c needs these, real
// implementations live in jsdrv.c (same pattern as pubsub_test.c)
struct jsdrvp_msg_s * jsdrvp_msg_alloc(struct jsdrv_context_s * context) {
    (void) context;
    struct jsdrvp_msg_s * m = jsdrv_alloc_clr(sizeof(struct jsdrvp_msg_s));
    jsdrv_list_initialize(&m->item);
    return m;
}

struct jsdrvp_msg_s * jsdrvp_msg_alloc_value(struct jsdrv_context_s * context, const char * topic, const struct jsdrv_union_s * value) {
    struct jsdrvp_msg_s * m = jsdrvp_msg_alloc(context);
    jsdrv_cstr_copy(m->topic, topic, sizeof(m->topic));
    m->value = *value;
    return m;
}

void jsdrvp_msg_free(struct jsdrv_context_s * context, struct jsdrvp_msg_s * msg) {
    (void) context;
    if (msg) {
        jsdrv_free(msg);
    }
}

static bool event_is_signaled(struct msg_queue_s * q) {
#if _WIN32
    return WAIT_OBJECT_0 == WaitForSingleObject(msg_queue_handle_get(q), 0);
#else
    struct pollfd fds = {
            .fd = msg_queue_handle_get(q),
            .events = POLLIN,
            .revents = 0,
    };
    return poll(&fds, 1, 0) > 0;
#endif
}

static struct jsdrvp_msg_s * msg_initialize(struct jsdrvp_msg_s * msg) {
    jsdrv_memset(msg, 0, sizeof(*msg));
    jsdrv_list_initialize(&msg->item);
    return msg;
}

static void test_fifo_order(void ** state) {
    (void) state;
    struct jsdrvp_msg_s m1, m2;
    struct msg_queue_s * q = msg_queue_init();
    assert_true(msg_queue_is_empty(q));
    msg_queue_push(q, msg_initialize(&m1));
    msg_queue_push(q, msg_initialize(&m2));
    assert_false(msg_queue_is_empty(q));
    assert_ptr_equal(&m1, msg_queue_pop_immediate(q));
    assert_ptr_equal(&m2, msg_queue_pop_immediate(q));
    assert_null(msg_queue_pop_immediate(q));
    msg_queue_finalize(q, NULL);
}

// Regression: pop_immediate must leave the event signaled while messages
// remain, or a waiter sleeps its full timeout with a queued message.
static void test_event_signaled_until_empty(void ** state) {
    (void) state;
    struct jsdrvp_msg_s m1, m2;
    struct msg_queue_s * q = msg_queue_init();
    assert_false(event_is_signaled(q));
    msg_queue_push(q, msg_initialize(&m1));
    msg_queue_push(q, msg_initialize(&m2));
    assert_true(event_is_signaled(q));
    assert_ptr_equal(&m1, msg_queue_pop_immediate(q));
    assert_true(event_is_signaled(q));    // m2 still queued
    assert_ptr_equal(&m2, msg_queue_pop_immediate(q));
    assert_false(event_is_signaled(q));   // empty -> reset
    msg_queue_finalize(q, NULL);
}

static void test_pop_empty_resets_event(void ** state) {
    (void) state;
    struct jsdrvp_msg_s m1;
    struct msg_queue_s * q = msg_queue_init();
    msg_queue_push(q, msg_initialize(&m1));
    assert_ptr_equal(&m1, msg_queue_pop_immediate(q));
    msg_queue_push(q, msg_initialize(&m1));   // re-push same message
    assert_ptr_equal(&m1, msg_queue_pop_immediate(q));
    assert_null(msg_queue_pop_immediate(q));  // empty pop also resets
    assert_false(event_is_signaled(q));
    msg_queue_finalize(q, NULL);
}

static void test_pop_with_timeout_drains_burst(void ** state) {
    (void) state;
    struct jsdrvp_msg_s m1, m2;
    struct jsdrvp_msg_s * m = NULL;
    struct msg_queue_s * q = msg_queue_init();
    msg_queue_push(q, msg_initialize(&m1));
    msg_queue_push(q, msg_initialize(&m2));
    assert_int_equal(0, msg_queue_pop(q, &m, 1000));
    assert_ptr_equal(&m1, m);
    // must return immediately, not wait out the timeout
    assert_int_equal(0, msg_queue_pop(q, &m, 0));
    assert_ptr_equal(&m2, m);
    msg_queue_finalize(q, NULL);
}

int main(void) {
    const struct CMUnitTest tests[] = {
            cmocka_unit_test(test_fifo_order),
            cmocka_unit_test(test_event_signaled_until_empty),
            cmocka_unit_test(test_pop_empty_resets_event),
            cmocka_unit_test(test_pop_with_timeout_drains_burst),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
