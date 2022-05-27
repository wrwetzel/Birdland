%define name fullword
%define version 1.0
%define unmangled_version 1.0
%define release 1

Summary: UNKNOWN
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: UNKNOWN
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: UNKNOWN <UNKNOWN>

%description
UNKNOWN

%prep
%setup -n %{name}-%{unmangled_version}

%build
env CFLAGS="$RPM_OPT_FLAGS" python3 setup.py build

%install
python3 setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
