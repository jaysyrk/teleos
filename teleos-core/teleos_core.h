#ifndef TELEOS_CORE_H
#define TELEOS_CORE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct TeleosHandle TeleosHandle;

TeleosHandle* teleos_from_str(const char* text);

TeleosHandle* teleos_from_file(const char* path);

int32_t teleos_ask(TeleosHandle* handle, const char* goal);

char* teleos_why(TeleosHandle* handle, const char* goal);

char* teleos_all(TeleosHandle* handle, const char* goal);

int32_t teleos_add_fact(TeleosHandle* handle, const char* fact);

void teleos_free_str(char* s);

void teleos_free(TeleosHandle* handle);

#ifdef __cplusplus
}
#endif

#endif
