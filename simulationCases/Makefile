# Check if .project_config exists
ifeq ($(wildcard ../.project_config),)
  $(error "../.project_config not found")
endif

BASILISK := $(shell . ../.project_config && echo $$BASILISK)

ifeq ($(strip $(BASILISK)),)
  $(error "BASILISK not set in .project_config")
endif

CFLAGS += -O2 -disable-dimensions
CFLAGS += -I$(PWD)/src-local -I$(PWD)/../src-local

.PHONY: fix-permissions
# Fix permissions for runtest script
fix-permissions:
	@chmod +x $(BASILISK)/src/runtest

# Make all test targets depend on fix-permissions
%.tst: fix-permissions

include $(BASILISK)/Makefile.defs