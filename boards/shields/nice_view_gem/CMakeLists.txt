if(CONFIG_ZMK_DISPLAY AND CONFIG_NICE_VIEW_WIDGET_STATUS)
  zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)
  zephyr_library_sources(custom_status_screen.c)
  zephyr_library_sources(assets/images.c)
  zephyr_library_sources(widgets/battery.c)
  zephyr_library_sources(widgets/output.c)
  zephyr_library_sources(widgets/util.c)

  zephyr_library_sources(widgets/animation.c)

  # Slideshow frames, on both halves.
  zephyr_library_sources(assets/campfire.c)
  zephyr_library_sources(assets/night.c)
  zephyr_library_sources(assets/astronaut.c)
  zephyr_library_sources(assets/tree.c)
  zephyr_library_sources(assets/cat.c)

  if(NOT CONFIG_ZMK_SPLIT OR CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    # Layer animation: only the central half knows the active layers.
    zephyr_library_sources(assets/gaming.c)
    zephyr_library_sources(widgets/screen.c)
  else()
    zephyr_library_sources(widgets/screen_peripheral.c)
  endif()
endif()
