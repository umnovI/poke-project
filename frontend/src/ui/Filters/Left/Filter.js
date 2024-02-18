"use client";

import { Sidebar } from "flowbite-react";
import { HiOutlineMinusSm, HiOutlinePlusSm } from "react-icons/hi";
import { twMerge } from "tailwind-merge";

export default function Category() {
  // Filters declaration
  // const filterOptions = [
  //   { name: "Type", key: 1 },
  //   { name: "Weakness", key: 2 },
  // ];

  return (
    <form action="#">
      <Sidebar aria-label="Filters">
        <Sidebar.Items>
          <Sidebar.ItemGroup>
            <Sidebar.Collapse
              label="Type"
              renderChevronIcon={(theme, open) => {
                const IconComponent = open ? HiOutlineMinusSm : HiOutlinePlusSm;
                return (
                  <IconComponent
                    aria-hidden
                    className={twMerge(
                      theme.label.icon.open[open ? "on" : "off"]
                    )}
                  />
                );
              }}
            >
              <input type="text" placeholder="Search" name="default" />
              <Item name="Default" />
            </Sidebar.Collapse>
          </Sidebar.ItemGroup>
        </Sidebar.Items>
      </Sidebar>
    </form>
  );
}

function Item({ name }) {
  console.log(name);
  return (
    <li className="flex items-center mb-4">
      <input
        id="TODO:MAKE-ME-UNIQUE-PLS"
        type="checkbox"
        value="I-NEED-VALUE"
        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
      />
      <label
        htmlFor="TODO:MAKE-ME-UNIQUE-PLS"
        className="ms-2 text-sm font-medium text-gray-900 dark:text-gray-300 cursor-pointer"
      >
        {name}
      </label>
    </li>
  );
}

// export default function Component() {
//   return (
//     <form className="filters grid grid-cols-1 gap-3">
//       One <br />
//       Two <br />
//       Three <br />
//       <div className="grid grid-cols-2">
//         <button type="submit" className="w-fit">
//           Filter
//         </button>
//         <button type="reset" className="w-fit">
//           Reset
//         </button>
//       </div>
//     </form>
//   );
// }
