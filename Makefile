all:

SELF_DIR := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))

override ___original_SHELL := $(SHELL)
override SHELL = \
	$(SELF_DIR)/my_shell.sh "$(CURDIR)" "$@" $(___original_SHELL)

TARGETS := foo bar

out := $(shell rm *.c)
$(warning >>> $(out))

-include other.mk
other.mk: remake
	echo '#...' >> other.mk

remake:
	touch $@

$(warning <<<)

.PHONY: all
all: $(TARGETS)

$(TARGETS): %: %.c
	cp $< $@

$(TARGETS:%=%.c):
	touch $@
