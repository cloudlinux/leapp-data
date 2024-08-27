# Parameters
DIST_NAME ?= cloudlinux
DIST_VERSION ?= 7
DIST_TARGET_VERSION := $(shell echo ${DIST_VERSION}+1 | bc)
GPG_KEY ?= RPM-GPG-KEY-CloudLinux RPM-GPG-KEY-AlmaLinux-$(DIST_TARGET_VERSION)
VENDORS = epel imunify kernelcare mariadb nginx-stable nginx-mainline postgresql

# Installation prefix
PREFIX?=/

# Variables
buildroot ?= build
_sysconfdir = /etc

# Directories
LEAPP_BUILD_DIR = $(buildroot)$(_sysconfdir)/leapp

VENDORS_DIR = $(LEAPP_BUILD_DIR)/files/vendors.d
VENDORS_GPG_DIR = $(VENDORS_DIR)/rpm-gpg

SOURCE_FILES_DIR = files/$(DIST_NAME)
TARGET_FILES_DIR = $(LEAPP_BUILD_DIR)/files

GPG_DIR_RHEL = $(LEAPP_BUILD_DIR)/repos.d/system_upgrade/common/files/rpm-gpg/$(DIST_TARGET_VERSION)/

all: vendors core

core:
	cp -arf files/$(DIST_NAME)/* $(buildroot)$(_sysconfdir)/leapp/files/

	install -D files/$(DIST_NAME)/leapp_upgrade_repositories.repo.el8 $(LEAPP_BUILD_DIR)/files/leapp_upgrade_repositories.repo
	install -D files/$(DIST_NAME)/repomap.json.el8 $(LEAPP_BUILD_DIR)/files/repomap.json

	@for key in $(GPG_KEY); do \
		install -D files/rpm-gpg/$${key} $(GPG_DIR_RHEL)/$${key}; \
	done

	find $(LEAPP_BUILD_DIR) -name '*.el?' -delete

vendors:
	mkdir -p $(VENDORS_DIR)
	cp -rf vendors.d/* $(VENDORS_DIR)/

	# expected to be almalinux here
	bash tools/generate_epel_files.sh "almalinux" "$(DIST_VERSION)" "$(buildroot)$(_sysconfdir)/leapp/files"

	@for vendor in $(VENDORS); do \
		install -D $(VENDORS_DIR)/$${vendor}.repo.el$(DIST_TARGET_VERSION) \
				$(VENDORS_DIR)/$${vendor}.repo; \
		install -D $(VENDORS_GPG_DIR)/$${vendor}.gpg.el$(DIST_TARGET_VERSION) \
				$(VENDORS_GPG_DIR)/$${vendor}.gpg; \
		install -D $(VENDORS_DIR)/$${vendor}_map.json.el$(DIST_TARGET_VERSION) \
				$(VENDORS_DIR)/$${vendor}_map.json; \
	done

	find $(LEAPP_BUILD_DIR) -name '*.el?' -delete

test:
	$(eval JSON_FILES := $(shell find $(buildroot) -path "./tests" -prune -o -name "*pes*.json*" -print0 | xargs -0 echo))

	python3 tests/validate_json.py tests/pes-events-schema.json $(JSON_FILES)
	python3 tests/validate_ids.py $(JSON_FILES)

	# todo: disabled temporary
	# python3 tests/check_debranding.py $(buildroot)$(_sysconfdir)/leapp/files/pes-events.json

install:
	cp -ar $(buildroot)/* $(PREFIX)

clean:
	rm -rf $(buildroot)

rpm:
	echo "Add your files to index before running this command"
	# see details here https://docs.oracle.com/en/operating-systems/oracle-linux/6/porting/ch10s01s03.html
	git ls-files -z | xargs -0 tar \
		-czvf ~/rpmbuild/SOURCES/$(shell rpm -q --queryformat="leapp-data-%{version}.tar.gz\n" --specfile leapp-data.spec) \
		--transform 's,^,$(shell rpm -q -D "dist_name cloudlinux" --queryformat="%{NAME}-%{VERSION}\n" --specfile leapp-data.spec)/,'

	rpmbuild -bb -D "dist_name cloudlinux" leapp-data.spec
